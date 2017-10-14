"""agents.py: Individual agents that will interact with the Havven market."""
import random

import model
from .marketplayer import MarketPlayer

class Randomizer(MarketPlayer):
    """Places random bids and asks near current market prices."""

    def __init__(self, unique_id: int, havven: "model.Havven",
                 fiat: float = 0.0, curits: float = 0.0,
                 nomins: float = 0.0,
                 variance: float = 0.05, order_lifetime: int = 30) -> None:
        super().__init__(unique_id, havven, fiat, curits, nomins)
        self.variance = variance
        """This agent will place orders within (+/-)variance*price of the going rate."""

        self.order_lifetime = order_lifetime
        """Orders older than this lifetime will be cancelled."""

    def step(self) -> None:
        condemned = []
        for order in self.orders:
            if order.book.time > order.time + self.order_lifetime:
                condemned.append(order)
        for order in condemned:
            order.cancel()

        action = random.choice([self._curit_fiat_bid_, self._curit_fiat_ask_,
                                self._nomin_fiat_bid_, self._nomin_fiat_ask_,
                                self._curit_nomin_bid_, self._curit_nomin_ask_])

        action()

    def _curit_fiat_bid_(self) -> None:
        price = self.model.market_manager.curit_fiat_market.price
        movement = round((2*random.random() - 1) *
                         price * self.variance, 3)
        self.place_curits_fiat_bid(self.fiat/10, price + movement)

    def _curit_fiat_ask_(self) -> None:
        price = self.model.market_manager.curit_fiat_market.price
        movement = round((2*random.random() - 1) *
                         price * self.variance, 3)
        self.place_curits_fiat_ask(self.fiat/10, price + movement)

    def _nomin_fiat_bid_(self) -> None:
        price = self.model.market_manager.nomin_fiat_market.price
        movement = round((2*random.random() - 1) *
                         price * self.variance, 3)
        self.place_nomins_fiat_bid(self.fiat/10, price + movement)

    def _nomin_fiat_ask_(self) -> None:
        price = self.model.market_manager.nomin_fiat_market.price
        movement = round((2*random.random() - 1) *
                         price * self.variance, 3)
        self.place_nomins_fiat_ask(self.fiat/10, price + movement)

    def _curit_nomin_bid_(self) -> None:
        price = self.model.market_manager.curit_nomin_market.price
        movement = round((2*random.random() - 1) *
                         price * self.variance, 3)
        self.place_curits_nomins_bid(self.fiat/10, price + movement)

    def _curit_nomin_ask_(self) -> None:
        price = self.model.market_manager.curit_nomin_market.price
        movement = round((2*random.random() - 1) *
                         price * self.variance, 3)
        self.place_curits_nomins_ask(self.fiat/10, price + movement)
