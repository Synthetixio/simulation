import random

from typing import Tuple, Optional
from decimal import Decimal as Dec

from agents import MarketPlayer
import orderbook as ob


class Speculator(MarketPlayer):
    """
    A speculator who comes into the market with one of the three currencies, buys the others,
      hoping the price will go up by profit_goal percent, before the hodl_duration passes

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

        self.active_trade_a: Optional[Tuple[Dec, int, 'ob.LimitOrder']] = None
        self.active_trade_b: Optional[Tuple[Dec, int, 'ob.LimitOrder']] = None

        self.change_currency(random.choice(["nomins", "curits", "fiat"]))

    def change_currency(self, currency):
        # remove active bids/aks
        if self.active_trade_a:
            self.active_trade_a[2].cancel()
            self.sell_a_function(self.a_currency())
            self.active_trade_a = None
        if self.active_trade_b:
            self.active_trade_b[2].cancel()
            self.sell_b_function(self.b_currency())
            self.active_trade_b = None

        self.primary_currency = currency

        if self.primary_currency == "nomins":
            self.avail_primary = lambda: self.available_nomins
            self.direction_a = "bid"
            self.a_currency = lambda: self.available_fiat
            self.market_a: ob.OrderBook = self.model.market_manager.nomin_fiat_market
            self.place_a_function = self.place_nomin_fiat_bid_with_fee
            self.sell_a_function = self.sell_fiat_for_nomins_with_fee

            self.direction_b = "ask"
            self.b_currency = lambda: self.available_curits
            self.market_b: ob.OrderBook = self.model.market_manager.curit_nomin_market
            self.place_b_function = self.place_curit_nomin_ask_with_fee
            self.sell_b_function = self.sell_curits_for_nomins_with_fee

        if self.primary_currency == "curits":
            self.avail_primary = lambda: self.available_curits
            self.direction_a = "bid"
            self.a_currency = lambda: self.available_nomins
            self.market_a: ob.OrderBook = self.model.market_manager.curit_nomin_market
            self.place_a_function = self.place_curit_nomin_bid_with_fee
            self.sell_a_function = self.sell_nomins_for_curits_with_fee

            self.direction_b = "bid"
            self.b_currency = lambda: self.available_fiat
            self.market_b: ob.OrderBook = self.model.market_manager.curit_fiat_market
            self.place_b_function = self.place_curit_fiat_bid_with_fee
            self.sell_b_function = self.sell_fiat_for_curits_with_fee

        if self.primary_currency == "fiat":
            self.avail_primary = lambda: self.available_fiat
            self.direction_a = "ask"
            self.a_currency = lambda: self.available_nomins
            self.market_a: ob.OrderBook = self.model.market_manager.nomin_fiat_market
            self.place_a_function = self.place_nomin_fiat_ask_with_fee
            self.sell_a_function = self.sell_nomins_for_fiat_with_fee

            self.direction_b = "ask"
            self.b_currency = lambda: self.available_curits
            self.market_b: ob.OrderBook = self.model.market_manager.curit_fiat_market
            self.place_b_function = self.place_curit_fiat_ask_with_fee
            self.sell_b_function = self.sell_curits_for_fiat_with_fee

    def step(self):
        if self.active_trade_a:
            if not self._check_trade_profit(*self.active_trade_a, self.direction_a):
                order = self.active_trade_a[2]
                order.cancel()
                self.sell_a_function(self.a_currency())
                self.active_trade_a = None

        if self.active_trade_b:
            if not self._check_trade_profit(*self.active_trade_b, self.direction_b):
                order = self.active_trade_b[2]
                order.cancel()
                self.sell_b_function(self.b_currency())
                self.active_trade_b = None

        if self.active_trade_a is None:
            self.active_trade_a = self.try_trade(
                self.a_currency, self.direction_a, self.market_a, self.place_a_function
            )
        if self.active_trade_b is None:
            self.active_trade_b = self.try_trade(
                self.b_currency, self.direction_b, self.market_b, self.place_b_function
            )

    def try_trade(self, avail_curr_func, direction, market, place_w_fee_function):
        if random.random() < self.risk_factor:
            if direction == "ask":
                price = market.highest_bid_price()
                market.buy(self.avail_primary()*self.investment_fraction, self)
                if avail_curr_func() > Dec(0.005):
                    price_goal = Dec(price*(1+self.profit_goal))
                    new_ask = place_w_fee_function(avail_curr_func(), price_goal)
                    if new_ask is not None:
                        return (
                            price,
                            self.model.manager.time,
                            new_ask
                        )
                    else:
                        return None
            else:  # placing bid
                price = market.lowest_ask_price()
                market.sell(self.avail_primary()*self.investment_fraction, self)
                if avail_curr_func() > Dec(0.005):
                    price_goal = Dec(price*(1-self.profit_goal))
                    new_bid = place_w_fee_function(avail_curr_func(), price_goal)
                    if new_bid is not None:
                        return (
                            price,
                            self.model.manager.time,
                            new_bid
                        )
                    else:
                        return None
        return None

    def _check_trade_profit(self, initial_price, time_bought, order, direction) -> bool:
        """
        Check the current trade, to see if the market is below the loss_cutoff or
        """
        if direction == "ask":
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
        elif direction == "bid":
            bid = order
            if not bid.active:
                return False

            current_price = bid.book.lowest_ask_price()

            if current_price < initial_price * (1 - self.profit_goal) and len(bid.book.bids) > 0:
                # the order should've been filled, i.e. it shouldn't be active
                raise Exception("order should've been filled")

            # the current trade is going down, get out
            if current_price > initial_price * (1 + self.loss_cutoff):
                return False

            # if the price is lower than the initial buy, and has been holding for longer than the duration
            if current_price > initial_price and time_bought + self.hodl_duration <= self.model.manager.time:
                return False

            # otherwise do nothing
            return True
        else:
            raise Exception("order in speculator _check_trade_profit is neither a bid nor ask type(order) =", type(order))
