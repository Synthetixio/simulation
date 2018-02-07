import random
from decimal import Decimal as Dec
from typing import Tuple, Optional, Callable

from agents import MarketPlayer
from core import orderbook as ob


class Speculator(MarketPlayer):
    """
    A speculator who comes into the market with one of the three currencies, buys the others,
      hoping the price will go up by profit_goal percent, before the hold_duration passes

    The speculator places asks after purchasing nom/hav at purchase_price*(1+profit_goal)
    If the market price goes below loss_cutoff, or the hold_duration passes, and the price is
      below the initial purchase price, sell

    This class only holds helper functions for the speculator types below
    """
    avail_primary = None

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.risk_factor = Dec(random.random() / 5 + 0.05)  # (5-25)%
        """How likely is the speculator going to place a trade if he
        doesn't have an active one"""

        self.hold_duration = Dec(random.randint(20, 30))
        """How long a speculator wants to hodl onto a trade"""

        self.profit_goal = Dec(random.random() / 10 + 0.01)  # (1-2)%
        """How much a speculator wants to profit on any trade"""

        self.loss_cutoff = Dec(random.random() / 20 + 0.01)  # (1-1.5)%
        """At what point does the speculator get rid of a trade"""

        self.investment_fraction = Dec(random.random() / 10 + 0.4)  # (40-50)%
        """How much wealth does the speculator throw into a trade"""

        self.primary_currency = random.choice(["havvens", "fiat", "nomins"])
        self.set_avail_primary()

    @property
    def name(self):
        """Add the primary currency to the name"""
        return f"{self.__class__.__name__} {self.unique_id} ({self.primary_currency})"

    def set_avail_primary(self):
        """
        Set functions for checking available primary currency, or raise an exception if
        the currency isn't one of the main 3
        """
        if self.primary_currency == "havvens":
            self.avail_primary = lambda: self.available_havvens
        elif self.primary_currency == "fiat":
            self.avail_primary = lambda: self.available_fiat
        elif self.primary_currency == "nomins":
            self.avail_primary = lambda: self.available_nomins
        else:
            raise Exception(f"currency:{self.primary_currency} isn't in [havvens, fiat, nomins]")

    def setup(self, init_value):
        self.wage_parameter = init_value/Dec(100)

        if self.primary_currency == "fiat":
            self.fiat = self.model.manager.round_decimal(init_value * Dec(3))
        elif self.primary_currency == "nomins":
            self.fiat = self.model.manager.round_decimal(init_value * Dec(3))
        elif self.primary_currency == "havvens":
            self.model.endow_havvens(
                self, self.model.manager.round_decimal(init_value * Dec(3))
            )

    def _check_trade_profit(self, initial_price, time_bought, order, direction) -> bool:
        """
        Check the current trade, to see if the price has gone above/below the loss cutoff or
        above/below the profit goal, if the speculator should cancel, return false, otherwise
        return true.
        """
        if direction == "ask":
            ask = order
            if not ask.active:
                return False

            current_price = ask.book.highest_bid_price()

            if current_price > initial_price * (1 + self.profit_goal) and len(ask.book.bids) > 0:
                # the order should've been filled, i.e. it shouldn't be active
                print(initial_price, current_price, order, direction)
                raise Exception("order should've been filled")

            # the current trade is going down, get out
            if current_price < initial_price * (1 - self.loss_cutoff):
                return False

            # if the price is lower than the initial buy, and has been holding for longer than the duration
            if current_price < initial_price and time_bought + self.hold_duration <= self.model.manager.time:
                return False

            # otherwise do nothing
            return True
        elif direction == "bid":
            bid = order
            if not bid.active:
                return False

            current_price = bid.book.lowest_ask_price()

            if current_price < initial_price * (1 - self.profit_goal) and len(bid.book.asks) > 0:
                print(initial_price, current_price, order, direction)

                # the order should've been filled, i.e. it shouldn't be active
                raise Exception("order should've been filled")

            # the current trade is going down, get out
            if current_price > initial_price * (1 + self.loss_cutoff):
                return False

            # if the price is lower than the initial buy, and has been holding for longer than the duration
            if current_price > initial_price and time_bought + self.hold_duration <= self.model.manager.time:
                return False

            # otherwise do nothing
            return True
        else:
            raise Exception(f""""order in speculator _check_trade_profit is neither a bid nor ask. 
                            type(order): {type(order)}""")

    def _try_trade(
            self,
            avail_curr_func: Callable[[], Dec],  # the amount of currency the player has that is being speculated on
            direction: str,  # the direction of the trade secondary->primary
            market: ob.OrderBook,  # the market being traded on
            place_w_fee_function: Callable[[Dec, Dec], 'ob.LimitOrder']  # place the order secondary->primary
    ) -> Optional[Tuple[Dec, int, 'ob.LimitOrder']]:
        """
        Attempt to make a trade if the speculator is "feeling" risky enough

        Making a trade involves buying into one of the markets, then deciding on a price
        to sell.
        """
        if random.random() < self.risk_factor:
            if direction == "ask":
                price = market.highest_bid_price()
                bid = market.bid(price, self.avail_primary() * self.investment_fraction, self)
                if bid is None:
                    return None
                bid.cancel()
                if avail_curr_func() > Dec(0.005):
                    price_goal = Dec(price * (1 + self.profit_goal))
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
                ask = market.ask(price, self.avail_primary() * self.investment_fraction, self)
                if ask is None:
                    return None
                ask.cancel()
                if avail_curr_func() > Dec(0.005):
                    price_goal = Dec(price * (1 - self.profit_goal))
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

    def step(self):
        super().step()


class HavvenSpeculator(Speculator):
    """
    This speculator will only speculate on the price of havvens, as he believes nom/fiat is stable

    They will trade between some primary and some secondary currency.

    If their primary currency is havvens, they will attempt to short havvens, hoping the price will
    drop. They will short by holding their secondary currency.

    If their primary currency is fiat or nomins, they will attempt to long havvens, hoping the price
    will rise.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.primary_currency = random.choice(["havvens", "havvens", "fiat", "nomins"])
        # give an equal chance to short/long havvens
        self.change_currency()

        self.set_avail_primary()
        self.active_trade: Optional[Tuple[Dec, int, 'ob.LimitOrder']] = None
        """tuple of [Price_at_purchase, time, order]"""

    def change_currency(self, currency: Optional[str] = None) -> None:
        """
        Change currency and trade functions for speculator for a more generalised trade function
        """
        if currency:
            self.primary_currency = currency
            self.set_avail_primary()

        if self.primary_currency == "havvens":
            self.secondary_currency = random.choice(["fiat", "nomins"])
            self.direction = "bid"
            if self.secondary_currency == "fiat":
                self.market = self.havven_fiat_market
                self.avail_secondary = lambda: self.available_fiat
                self.place_function = self.place_havven_fiat_bid_with_fee
                self.sell_function = self.sell_fiat_for_havvens_with_fee
            else:  # secondary: nomins
                self.market = self.havven_nomin_market
                self.avail_secondary = lambda: self.available_nomins
                self.place_function = self.place_nomin_fiat_bid_with_fee
                self.sell_function = self.sell_nomins_for_havvens_with_fee

        elif self.primary_currency == "fiat":
            self.secondary_currency = "havvens"
            self.avail_secondary = lambda: self.available_havvens
            self.market = self.havven_fiat_market
            self.direction = "ask"
            self.place_function = self.place_havven_fiat_ask_with_fee
            self.sell_function = self.sell_havvens_for_fiat_with_fee

        else:  # primary: nomins
            self.secondary_currency = "havvens"
            self.avail_secondary = lambda: self.available_havvens
            self.market = self.havven_nomin_market
            self.direction = "ask"
            self.place_function = self.place_havven_nomin_ask_with_fee
            self.sell_function = self.sell_havvens_for_nomins_with_fee

    def step(self):
        super().step()

        if self.primary_currency == "nomins":
            if self.available_fiat > 0:
                self.sell_fiat_for_nomins_with_fee(self.available_fiat)

        if self.active_trade:
            if not self._check_trade_profit(*self.active_trade, self.direction):
                self.active_trade[2].cancel()
                self.sell_function(self.avail_secondary())
                self.active_trade = None
        else:
            if self.avail_secondary() > 0:
                self.sell_function(self.avail_secondary())

            self.active_trade = self._try_trade(
                self.avail_secondary, self.direction, self.market, self.place_function
            )


class NaiveSpeculator(Speculator):
    """
    This speculator believes the nom/fiat market can plummet or go to the moon, i.e. it is like
      any other market to speculate on
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.active_trade_a: Optional[Tuple[Dec, int, 'ob.LimitOrder']] = None
        """tuple of [Price_at_purchase, time, order]"""
        self.active_trade_b: Optional[Tuple[Dec, int, 'ob.LimitOrder']] = None
        """tuple of [Price_at_purchase, time, order]"""

    def setup(self, init_value):
        super().setup(init_value)

        self.change_currency()

    def change_currency(self, currency: Optional[str] = None) -> None:
        """
        Change currency and trade functions for speculator for a more generalised trade function
        """
        if currency:
            self.primary_currency = currency
            self.set_avail_primary()

        # remove active bids/aks
        if self.active_trade_a:
            self.active_trade_a[2].cancel()
            self.sell_a_function(self.a_currency())
            self.active_trade_a = None
        if self.active_trade_b:
            self.active_trade_b[2].cancel()
            self.sell_b_function(self.b_currency())
            self.active_trade_b = None

        if self.primary_currency == "nomins":
            self.avail_primary = lambda: self.available_nomins
            self.direction_a = "bid"
            self.a_currency = lambda: self.available_fiat
            self.market_a: ob.OrderBook = self.model.market_manager.nomin_fiat_market
            self.place_a_function = self.place_nomin_fiat_bid_with_fee
            self.sell_a_function = self.sell_fiat_for_nomins_with_fee

            self.direction_b = "ask"
            self.b_currency = lambda: self.available_havvens
            self.market_b: ob.OrderBook = self.model.market_manager.havven_nomin_market
            self.place_b_function = self.place_havven_nomin_ask_with_fee
            self.sell_b_function = self.sell_havvens_for_nomins_with_fee

        if self.primary_currency == "havvens":
            self.avail_primary = lambda: self.available_havvens
            self.direction_a = "bid"
            self.a_currency = lambda: self.available_nomins
            self.market_a: ob.OrderBook = self.model.market_manager.havven_nomin_market
            self.place_a_function = self.place_havven_nomin_bid_with_fee
            self.sell_a_function = self.sell_nomins_for_havvens_with_fee

            self.direction_b = "bid"
            self.b_currency = lambda: self.available_fiat
            self.market_b: ob.OrderBook = self.model.market_manager.havven_fiat_market
            self.place_b_function = self.place_havven_fiat_bid_with_fee
            self.sell_b_function = self.sell_fiat_for_havvens_with_fee

        if self.primary_currency == "fiat":
            self.avail_primary = lambda: self.available_fiat
            self.direction_a = "ask"
            self.a_currency = lambda: self.available_nomins
            self.market_a: ob.OrderBook = self.model.market_manager.nomin_fiat_market
            self.place_a_function = self.place_nomin_fiat_ask_with_fee
            self.sell_a_function = self.sell_nomins_for_fiat_with_fee

            self.direction_b = "ask"
            self.b_currency = lambda: self.available_havvens
            self.market_b: ob.OrderBook = self.model.market_manager.havven_fiat_market
            self.place_b_function = self.place_havven_fiat_ask_with_fee
            self.sell_b_function = self.sell_havvens_for_fiat_with_fee

    def step(self) -> None:
        super().step()

        if self.active_trade_a:
            if not self._check_trade_profit(*self.active_trade_a, self.direction_a):
                order = self.active_trade_a[2]
                order.cancel()
                self.sell_a_function(self.a_currency())
                self.active_trade_a = None
        else:
            if self.a_currency() > 0:
                self.sell_a_function(self.a_currency())

            self.active_trade_a = self._try_trade(
                self.a_currency, self.direction_a, self.market_a, self.place_a_function
            )

        if self.active_trade_b:
            if not self._check_trade_profit(*self.active_trade_b, self.direction_b):
                order = self.active_trade_b[2]
                order.cancel()
                self.sell_b_function(self.b_currency())
                self.active_trade_b = None
        else:
            if self.b_currency() > 0:
                self.sell_b_function(self.b_currency())

            self.active_trade_b = self._try_trade(
                self.b_currency, self.direction_b, self.market_b, self.place_b_function
            )
