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

    If the price is higher than the initial price,
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.risk_factor = Dec(random.random()/5+0.1)

        self.hodl_duration = Dec(random.randint(5, 10))
        """How long a speculator wants to hold onto a trade"""

        self.profit_goal = Dec(random.random()/50 + 0.005)
        """How much a speculator wants to profit on any trade"""

        self.loss_cutoff = Dec(random.random()/80 + 0.003)
        """At what point does the speculator get rid of a trade"""

        self.investment_fraction = Dec(random.random()/10 + 0.1)
        """How much wealth does the speculator throw into a trade"""

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
            self._check_trade_profit(*self.active_curit_trade)
        if self.active_nomin_trade:
            self._check_trade_profit(*self.active_nomin_trade)

        if self.active_curit_trade is None:
            if random.random() < self.risk_factor:
                price = self.model.market_manager.curit_fiat_market.highest_bid_price()
                self.sell_fiat_for_curits_with_fee(self.fiat/self.investment_fraction)
                # this should fill instantly
                self.active_curit_trade = (
                    price,
                    self.model.manager.time,
                    self.place_curit_fiat_ask(self.available_curits, price*(1+self.profit_goal))
                )

        if self.active_nomin_trade is None:
            if random.random() < self.risk_factor:
                price = self.model.market_manager.nomin_fiat_market.highest_bid_price()
                self.sell_fiat_for_nomins_with_fee(self.fiat / self.investment_fraction)
                # this should fill instantly
                self.active_nomin_trade = (
                    price,
                    self.model.manager.time,
                    self.place_nomin_fiat_ask(self.available_nomins, price * (1 + self.profit_goal))
                )

    def _check_trade_profit(self, initial_price, time_bought, ask):
        """
        Check the current trade, to see if the market is below the loss_cutoff or
        """
        if not ask.active:
            self.active_curit_trade = None
            return

        current_price = ask.book.highest_bid_price()

        if current_price > initial_price * (1 + self.profit_goal):
            # the order should've been filled, i.e. it shouldn't be active
            raise Exception("order should've been filled")
            pass

        # the current trade is going down, get out
        if current_price < initial_price * (1 - self.loss_cutoff):
            ask.cancel()
            self.active_curit_trade = None
            ask.book.sell(ask.quantity, self)
            return

        # if the price is lower than the initial buy, and has been holding for longer than the duration
        if current_price < initial_price and time_bought + self.hodl_duration > self.model.manager.time:
            ask.cancel()
            self.active_curit_trade = None
            self.sell_nomins_for_fiat_with_fee(ask.quantity)
            return
        # otherwise do nothing
