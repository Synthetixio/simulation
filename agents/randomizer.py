"""agents.py: Individual agents that will interact with the Havven market."""
import random
from decimal import Decimal as Dec

from core import orderbook as ob
from managers import HavvenManager as hm
from .marketplayer import MarketPlayer


class Randomizer(MarketPlayer):
    """Places random bids and asks near current market prices."""

    def __init__(self, unique_id: int, havven_model: "model.HavvenModel",
                 fiat: Dec = Dec(0),
                 havvens: Dec = Dec(0),
                 nomins: Dec = Dec(0),
                 variance: Dec = Dec(0.02),
                 order_lifetime: int = 30,
                 max_orders: int = 10) -> None:
        super().__init__(unique_id, havven_model, fiat, havvens, nomins)
        self.variance = variance
        """This agent will place orders within (+/-)variance*price of the going rate."""

        self.order_lifetime = order_lifetime
        """Orders older than this lifetime will be cancelled."""

        self.max_orders = max_orders
        """Don't submit more than this number of orders."""

    def setup(self, init_value: Dec):
        self.wage_parameter = init_value/Dec(100)

        self.fiat = init_value
        self.model.endow_havvens(self, Dec(3) * init_value)

    def step(self) -> None:
        super().step()

        # Cancel expired orders
        condemned = []
        for order in self.orders:
            if order.book.time > order.time + self.order_lifetime:
                condemned.append(order)
        for order in condemned:
            order.cancel()

        if len(self.orders) < self.max_orders:
            action = random.choice([self._havven_fiat_bid, self._havven_fiat_ask,
                                    self._nomin_fiat_bid, self._nomin_fiat_ask,
                                    self._havven_nomin_bid, self._havven_nomin_ask])
            if action() is None:
                return

    def _havven_fiat_bid(self) -> "ob.Bid":
        price = self.havven_fiat_market.price
        movement = hm.round_decimal(Dec(2 * random.random() - 1) * price * self.variance)
        return self.place_havven_fiat_bid(self._fraction(self.available_fiat, Dec(10)), price + movement)

    def _havven_fiat_ask(self) -> "ob.Ask":
        price = self.havven_fiat_market.price
        movement = hm.round_decimal(Dec(2 * random.random() - 1) * price * self.variance)
        return self.place_havven_fiat_ask(self._fraction(self.available_havvens, Dec(10)), price + movement)

    def _nomin_fiat_bid(self) -> "ob.Bid":
        price = self.nomin_fiat_market.price
        movement = hm.round_decimal(Dec(2 * random.random() - 1) * price * self.variance)
        return self.place_nomin_fiat_bid(self._fraction(self.available_fiat, Dec(10)), price + movement)

    def _nomin_fiat_ask(self) -> "ob.Ask":
        price = self.nomin_fiat_market.price
        movement = hm.round_decimal(Dec(2 * random.random() - 1) * price * self.variance)
        return self.place_nomin_fiat_ask(self._fraction(self.available_nomins, Dec(10)), price + movement)

    def _havven_nomin_bid(self) -> "ob.Bid":
        price = self.havven_nomin_market.price
        movement = hm.round_decimal(Dec(2 * random.random() - 1) * price * self.variance)
        return self.place_havven_nomin_bid(self._fraction(self.available_nomins, Dec(10)), price + movement)

    def _havven_nomin_ask(self) -> "ob.Ask":
        price = self.havven_nomin_market.price
        movement = hm.round_decimal(Dec(2 * random.random() - 1) * price * self.variance)
        return self.place_havven_nomin_ask(self._fraction(self.available_havvens, Dec(10)), price + movement)
