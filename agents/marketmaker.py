"""
http://www.eecs.harvard.edu/cs286r/courses/fall12/papers/OPRS10.pdf
http://www.cs.cmu.edu/~aothman/
"""

import random
from decimal import Decimal as Dec
from typing import Dict, Any, Optional

from agents import MarketPlayer
from core import orderbook as ob


class MarketMaker(MarketPlayer):
    """
    Market makers in general have four desiderata:
    (1) bounded loss
    (2) the ability to make a profit
    (3) a vanishing bid/ask spread
    (4) unlimited market depth

    This market maker uses Fixed prices with shrinking profit cut

    Probably the simplest automated market maker is to determine a probability distribution
    over the future states of the world, and to offer to make bets directly at those odds.

    If we allow the profit cut to diminish to zero as trading volume increases, the resulting
    market maker has three of the four desired properties: the ability to make a profit,
    a vanishing marginal bid/ask spread, and unbounded depth in limit.

    However, it still has unbounded worst-case loss because a trader with knowledge of the
    true future could make an arbitrarily large winning bet with the market maker.

    To calculate the probability of the future state, a simple gradient on the moving average
    will be used.

    In the case where the market maker believes the price will rise, it will place a sell at a
    set price in the for the future, and slowly buy at higher and higher prices
    |                      _--_
    |          ========   (moon)
    |  ========       ---  "--"
    |==          -----
    |       -----   ===
    |  -----     ===
    |--       ===
    |      ===
    |   ===
    |===
    | -> Time
    = Market maker's bid/ask spread
    - Predicted price movement
    the price difference is dependant on the gradient
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.last_bet_end: int = random.randint(-20, 10)
        '''How long since the last market maker's "bet"'''

        self.minimal_wait: int = 10
        '''How long will the market maker wait since it's last "bet" to let the market move on its own'''

        self.bet_duration: int = 30
        '''How long will the market maker do its "bet" for'''

        self.bet_percentage: Dec = Dec('1')
        '''
        How much of it's wealth will the market maker use on a "bet"
        The bot will constantly update the orders on either side to use all it's wealth
        multiplied by the percentage value
        '''

        self.initial_bet_margin: Dec = Dec('0.05')
        '''
        How off the expected price gradient will the bets be placed initially
        '''

        self.ending_bet_margin: Dec = Dec('0.01')
        '''
        How close the bets get at the end
        '''

        self.minimal_price: Dec = Dec('0.0001')

        self.trade_market = random.choice([
            self.havven_fiat_market,
            self.nomin_fiat_market,
            self.havven_nomin_market
        ])

        self.current_bet: Optional[Dict[str, Any[str, int, Dec, 'ob.LimitOrder']]] = None

    @property
    def name(self) -> str:
        return f"{self.__class__.__name__} {self.unique_id} ({self.trade_market.name})"

    def setup(self, init_value) -> None:
        """
        Initially give the players the two currencies of their trade_market
        if they trade in nomins, start with fiat instead, to purchase the nomins
        """
        self.wage_parameter = init_value/Dec(100)

        if self.trade_market == self.havven_fiat_market:
            self.fiat = init_value * Dec(5)
            self.model.endow_havvens(self, init_value * Dec(5))
        if self.trade_market == self.havven_nomin_market:
            self.fiat = init_value * Dec(5)
            self.model.endow_havvens(self, init_value * Dec(5))
        if self.trade_market == self.nomin_fiat_market:
            self.fiat = init_value * Dec(5)

    def step(self) -> None:
        super().step()

        # don't do anything until only holding the correct two currencies
        if self.trade_market == self.havven_nomin_market:
            if self.available_fiat > 0:
                self.sell_fiat_for_havvens_with_fee(self.available_fiat / Dec(2))
                self.sell_fiat_for_nomins_with_fee(self.available_fiat)
        if self.trade_market == self.nomin_fiat_market:
            if self.available_havvens > 0:
                self.sell_havvens_for_fiat_with_fee(self.available_havvens / Dec(2))
                self.sell_havvens_for_nomins_with_fee(self.available_havvens)
        if self.trade_market == self.havven_fiat_market:
            if self.available_nomins > 0:
                self.sell_nomins_for_fiat_with_fee(self.available_nomins / Dec(2))
                self.sell_nomins_for_havvens_with_fee(self.available_nomins)

        # if the duration has ended, close the trades
        if self.last_bet_end >= self.minimal_wait + self.bet_duration:
            self.last_bet_end = 0
            self.current_bet['bid'].cancel()
            self.current_bet['ask'].cancel()
            self.current_bet = None
        # if the duration hasn't ended, update the trades
        elif self.current_bet is not None:
            # update both bid and ask every step in case orders were partially filled
            # so that quantities are updated
            self.current_bet['bid'].cancel()
            self.current_bet['ask'].cancel()
            bid = self.place_bid_func(
                self.last_bet_end - self.minimal_wait,
                self.current_bet['gradient'],
                self.current_bet['initial_price']
            )
            if bid is None:
                self.current_bet = None
                self.last_bet_end = 0
                return
            ask = self.place_ask_func(
                self.last_bet_end - self.minimal_wait,
                self.current_bet['gradient'],
                self.current_bet['initial_price']
            )
            if ask is None:
                bid.cancel()
                self.current_bet = None
                self.last_bet_end = 0
                return
            self.current_bet['bid'] = bid
            self.current_bet['ask'] = ask

        # if the minimal wait period has ended, create a bet
        elif self.last_bet_end >= self.minimal_wait:
            self.last_bet_end = self.minimal_wait
            gradient = self.calculate_gradient(self.trade_market)
            if gradient is None:
                return
            start_price = self.trade_market.price

            bid = self.place_bid_func(
                0,
                gradient,
                start_price
            )
            if bid is None:
                return

            ask = self.place_ask_func(
                0,
                gradient,
                start_price
            )
            if ask is None:
                bid.cancel()
                return

            self.current_bet = {
                'gradient': gradient,
                'initial_price': start_price,
                'bid': bid,
                'ask': ask
            }
        self.last_bet_end += 1

    def place_bid_func(self, time_in_effect: int, gradient: Dec, start_price: Dec) -> "ob.Bid":
        """
        Place a bid at a price dependent on the time in effect and gradient
        based on the player's margins

        The price chosen is the current predicted price (start + gradient * time_in_effect)
        multiplied by the current bet margin 1-(fraction of time remaining)*(max-min margin)+min_margin
        """
        price = start_price + Dec(gradient * time_in_effect)
        price = max(self.minimal_price, price)
        multiplier = 1 - (
            (Dec((self.bet_duration - time_in_effect) / self.bet_duration) *
             (self.initial_bet_margin - self.ending_bet_margin)
             ) + self.ending_bet_margin
        )
        if self.trade_market == self.nomin_fiat_market:
            return self.place_nomin_fiat_bid_with_fee(
                self.available_fiat * self.bet_percentage / price,
                price * multiplier
            )
        elif self.trade_market == self.havven_fiat_market:
            return self.place_havven_fiat_bid_with_fee(
                self.available_fiat * self.bet_percentage / price,
                price * multiplier
            )
        elif self.trade_market == self.havven_nomin_market:
            return self.place_havven_nomin_bid_with_fee(
                self.available_havvens * self.bet_percentage / price,
                price * multiplier
            )

    def place_ask_func(self, time_in_effect: int, gradient: Dec, start_price: Dec) -> "ob.Ask":
        """
        Place an ask at a price dependent on the time in effect and gradient
        based on the player's margins

        The price chosen is the current predicted price (start + gradient * time_in_effect)
        multiplied by the current bet margin 1+(fraction of time remaining)*(max-min margin)+min_margin
        """
        price = start_price + Dec(gradient * time_in_effect)
        price = max(self.minimal_price*2, price)  # do 2x minimal for ask, as bids and asks will have same price
        multiplier = 1 + (
            (Dec((self.bet_duration - time_in_effect) / self.bet_duration) *
             (self.initial_bet_margin - self.ending_bet_margin)
             ) + self.ending_bet_margin
        )
        if self.trade_market == self.nomin_fiat_market:
            return self.place_nomin_fiat_ask_with_fee(self.available_nomins * self.bet_percentage, price * multiplier)
        elif self.trade_market == self.havven_fiat_market:
            return self.place_havven_fiat_ask_with_fee(self.available_havvens * self.bet_percentage, price * multiplier)
        elif self.trade_market == self.havven_nomin_market:
            return self.place_havven_nomin_ask_with_fee(self.available_nomins * self.bet_percentage, price * multiplier)

    def calculate_gradient(self, trade_market: 'ob.OrderBook') -> Optional[Dec]:
        """
        Calculate the gradient of the moving average by taking the difference of the last two points
        """
        if len(trade_market.price_data) < 2:
            return None
        return (trade_market.price_data[-1] - trade_market.price_data[-2]) / 2
