import random

from typing import Tuple, Optional
from decimal import Decimal as Dec

from agents import MarketPlayer
import orderbook as ob


class Speculator(MarketPlayer):
    """
    A speculator who comes into the market with FIAT, buys both nomins and curits,
      hoping the price will go up by profit_goal percent, before the hodl_duration
      passes

    The speculator places asks after purchasing nom/cur at purchase_price*(1+profit_goal)
    If the market price goes below loss_cutoff, or the hodl_duration passes, and the price is
      below the initial purchase price, sell
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.risk_factor = Dec(random.random()/5+0.05)

        self.hodl_duration = Dec(random.randint(20, 30))
        """How long a speculator wants to hold onto a trade"""

        self.profit_goal = Dec(random.random()/50 + 0.008)
        """How much a speculator wants to profit on any trade"""

        self.loss_cutoff = Dec(random.random()/80 + 0.01)
        """At what point does the speculator get rid of a trade"""

        self.investment_fraction = Dec(random.random()/10 + 0.1)
        """How much wealth does the speculator throw into a trade"""

    def _check_trade_profit(self, initial_price, time_bought, order) -> bool:
        """
        Check the current trade, to see if the market is below the loss_cutoff or
        """
        if type(order) == ob.Ask:
            ask = order
            if not ask.active:
                return False

            current_price = ask.book.highest_bid_price()

            if current_price > initial_price * (1 + self.profit_goal) and len(ask.book.bids) > 0:
                # the order should've been filled, i.e. it shouldn't be active
                raise Exception("order should've been filled")

            # the current trade is going down, get out
            if current_price < initial_price * (1 - self.loss_cutoff):
                return False

            # if the price is lower than the initial buy, and has been holding for longer than the duration
            if current_price < initial_price and time_bought + self.hodl_duration <= self.model.manager.time:
                return False

            # otherwise do nothing
            return True
        elif type(order) == ob.Bid:
            return False
        else:
            raise Exception("order in speculator _check_trade_profit is neither a bid nor ask type(order) =", type(order))


class FiatSpeculator(Speculator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.active_nomin_trade: Optional[Tuple[Dec, int, 'ob.Ask']] = None
        self.active_curit_trade: Optional[Tuple[Dec, int, 'ob.Ask']] = None
        """
        Active trade consisting of
         - the price the speculation was bought at
         - the time the speculation was bought at
         - an ask placed at the profit ration
        """

    def step(self) -> None:
        if self.active_curit_trade:
            if not self._check_trade_profit(*self.active_curit_trade):
                ask = self.active_curit_trade[2]
                ask.cancel()
                self.sell_curits_for_fiat_with_fee(ask.quantity)
                self.active_curit_trade = None

        if self.active_nomin_trade:
            if not self._check_trade_profit(*self.active_nomin_trade):
                ask = self.active_nomin_trade[2]
                ask.cancel()
                self.sell_nomins_for_fiat_with_fee(ask.quantity)
                self.active_nomin_trade = None

        if self.active_curit_trade is None:
            if random.random() < self.risk_factor:
                price = self.model.market_manager.curit_fiat_market.lowest_ask_price()
                self.sell_fiat_for_curits_with_fee(self.available_fiat * self.investment_fraction)
                # this should fill instantly

                if self.available_curits > Dec(0.005):
                    new_ask = self.place_curit_fiat_ask_with_fee(self.available_curits, price*(1+self.profit_goal))
                    if new_ask is not None:
                        self.active_curit_trade = (
                            price,
                            self.model.manager.time,
                            new_ask
                        )
                    else:
                        self.active_curit_trade = None

        if self.active_nomin_trade is None:
            if random.random() < self.risk_factor:
                price = self.model.market_manager.nomin_fiat_market.highest_bid_price()
                self.sell_fiat_for_nomins_with_fee(self.available_fiat * self.investment_fraction)
                # this should fill instantly

                if self.available_nomins > Dec(0.005):
                    new_ask = self.place_nomin_fiat_ask_with_fee(self.available_nomins, price * (1 + self.profit_goal))
                    if new_ask is not None:
                        self.active_nomin_trade = (
                            price,
                            self.model.manager.time,
                            new_ask
                        )
                    else:
                        print(self.available_nomins, price * (1 + self.profit_goal))
                        self.active_nomin_trade = None


class NominSpeculator(Speculator):
    """
    Holds nomins and speculates on the nom/fiat and nom/cur markets
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.active_fiat_trade: Optional[Tuple[Dec, int, 'ob.Bid']] = None
        self.active_curit_trade: Optional[Tuple[Dec, int, 'ob.Ask']] = None
        """
        Active trade consisting of
         - the price the speculation was bought at
         - the time the speculation was bought at
         - an ask placed at the profit ration
        """

    def step(self) -> None:
        if self.active_curit_trade:
            if not self._check_trade_profit(*self.active_curit_trade):
                ask = self.active_curit_trade[2]
                ask.cancel()
                self.sell_curits_for_fiat_with_fee(ask.quantity)
                self.active_curit_trade = None

        if self.active_curit_trade is None:
            if random.random() < self.risk_factor:
                price = self.model.market_manager.curit_nomin_market.lowest_ask_price()
                self.sell_nomins_for_curits_with_fee(self.available_nomins * self.investment_fraction)
                # this should fill instantly

                if self.available_curits > Dec(0.005):
                    new_ask = self.place_curit_nomin_ask_with_fee(self.available_curits, price*(1+self.profit_goal))
                    if new_ask is not None:
                        self.active_curit_trade = (
                            price,
                            self.model.manager.time,
                            new_ask
                        )
                    else:
                        self.active_curit_trade = None

        if self.active_fiat_trade:
            if not self._check_trade_profit(*self.active_fiat_trade):
                ask = self.active_fiat_trade[2]
                ask.cancel()
                self.sell_fiat_for_nomins_with_fee(ask.quantity)
                self.active_fiat_trade = None

        if self.active_fiat_trade is None:
            if random.random() < self.risk_factor:
                price = self.model.market_manager.nomin_fiat_market.lowest_ask_price()
                self.sell_nomins_for_fiat_with_fee(self.available_nomins * self.investment_fraction)
                # this should fill instantly

                if self.available_fiat > Dec(0.005):
                    bid_price = price * (1 - self.profit_goal)
                    new_bid = self.place_nomin_fiat_bid_with_fee(self.available_nomins/bid_price, bid_price)
                    if new_bid is not None:
                        self.active_fiat_trade = (
                            price,
                            self.model.manager.time,
                            new_bid
                        )
                    else:
                        print(self.available_nomins, price * (1 + self.profit_goal))
                        self.active_fiat_trade = None
