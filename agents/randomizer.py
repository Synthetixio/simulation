"""agents.py: Individual agents that will interact with the Havven market."""
import random
from decimal import Decimal as Dec

import model
from managers import HavvenManager as hm
from .marketplayer import MarketPlayer
import orderbook as ob


class Randomizer(MarketPlayer):
    """Places random bids and asks near current market prices."""

    def __init__(self, unique_id: int, havven_model: "model.HavvenModel",
                 fiat: Dec = Dec(0),
                 curits: Dec = Dec(0.0),
                 nomins: Dec = Dec(0),
                 variance: Dec = Dec(0.02),
                 order_lifetime: int = 30,
                 max_orders: int = 10) -> None:
        super().__init__(unique_id, havven_model, fiat, curits, nomins)
        self.variance = variance
        """This agent will place orders within (+/-)variance*price of the going rate."""

        self.order_lifetime = order_lifetime
        """Orders older than this lifetime will be cancelled."""

        self.max_orders = max_orders
        """Don't submit more than this number of orders."""

    def step(self) -> None:
        # Cancel expired orders
        condemned = []
        for order in self.orders:
            if order.book.time > order.time + self.order_lifetime:
                condemned.append(order)
        for order in condemned:
            order.cancel()

        while len(self.orders) < self.max_orders:
            action = random.choice([self._curit_fiat_bid_, self._curit_fiat_ask_,
                                    self._nomin_fiat_bid_, self._nomin_fiat_ask_,
                                    self._curit_nomin_bid_, self._curit_nomin_ask_])
            if action() is None:
                break

    def _curit_fiat_bid_(self) -> "ob.Bid":
        price = self.curit_fiat_market.price
        movement = hm.round_decimal(Dec(2*random.random() - 1) * price * self.variance)
        return self.place_curit_fiat_bid(self._fraction_(self.available_fiat, Dec(10)), price + movement)

    def _curit_fiat_ask_(self) -> "ob.Ask":
        price = self.curit_fiat_market.price
        movement = hm.round_decimal(Dec(2*random.random() - 1) * price * self.variance)
        return self.place_curit_fiat_ask(self._fraction_(self.available_curits, Dec(10)), price + movement)

    def _nomin_fiat_bid_(self) -> "ob.Bid":
        price = self.nomin_fiat_market.price
        movement = hm.round_decimal(Dec(2*random.random() - 1) * price * self.variance)
        return self.place_nomin_fiat_bid(self._fraction_(self.available_fiat, Dec(10)), price + movement)

    def _nomin_fiat_ask_(self) -> "ob.Ask":
        price = self.nomin_fiat_market.price
        movement = hm.round_decimal(Dec(2*random.random() - 1) * price * self.variance)
        return self.place_nomin_fiat_ask(self._fraction_(self.available_nomins, Dec(10)), price + movement)

    def _curit_nomin_bid_(self) -> "ob.Bid":
        price = self.curit_nomin_market.price
        movement = hm.round_decimal(Dec(2*random.random() - 1) * price * self.variance)
        return self.place_curit_nomin_bid(self._fraction_(self.available_nomins, Dec(10)), price + movement)

    def _curit_nomin_ask_(self) -> "ob.Ask":
        price = self.curit_nomin_market.price
        movement = hm.round_decimal(Dec(2*random.random() - 1) * price * self.variance)
        return self.place_curit_nomin_ask(self._fraction_(self.available_curits, Dec(10)), price + movement)
