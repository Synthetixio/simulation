"""agents.py: Individual agents that will interact with the Havven market."""
from typing import Set, Tuple
import random

from mesa import Agent

from orderbook import Order, Ask, Bid
import model

class MarketPlayer(Agent):
    """
    A generic agent with a fixed initial wealth in fiat, with which it must buy into the market.
    The agent may escrow curits in order to issue nomins, and use various strategies in order
    to trade in the marketplace. Its aim is to increase its own wealth.
    """

    def __init__(self, unique_id: int, havven: model.Havven,
                 fiat: float = 0.0, curits: float = 0.0, nomins: float = 0.0) -> None:
        super().__init__(unique_id, havven)
        self.name: str = f"Player {unique_id}"
        self.fiat: float = fiat
        self.curits: float = curits
        self.nomins: float = nomins
        self.escrowed_curits: float = 0.0
        self.issued_nomins: float = 0.0

        self.initial_wealth: float = self.wealth()

        self.orders: Set[Order] = set()

    def __str__(self) -> str:
        return self.name

    def wealth(self) -> float:
        """Return the total wealth of this agent at current fiat prices."""
        return self.model.fiat_value(self.curits + self.escrowed_curits,
                                     self.nomins - self.issued_nomins,
                                     self.fiat)

    def profit(self) -> float:
        """Return the total profit accrued over the initial wealth. May be negative."""
        return self.wealth() - self.initial_wealth

    def profit_fraction(self) -> float:
        """Return profit accrued as a fraction of initial wealth. May be negative."""
        if self.initial_wealth != 0:
            return self.profit() / self.initial_wealth
        else:
            return 0

    def transfer_fiat_to(self, recipient: "MarketPlayer", value: float) -> bool:
        """Transfer a positive value of fiat to the recipient, if balance is sufficient. """ \
        """Return True on success."""
        return self.model.transfer_fiat(self, recipient, value)

    def transfer_curits_to(self, recipient: "MarketPlayer", value: float) -> bool:
        """Transfer a positive value of curits to the recipient, if balance is sufficient. """ \
        """Return True on success."""
        return self.model.transfer_curits(self, recipient, value)

    def transfer_nomins_to(self, recipient: "MarketPlayer", value: float) -> bool:
        """Transfer a positive value of nomins to the recipient, if balance is sufficient. """ \
        """Return True on success."""
        return self.model.transfer_nomins(self, recipient, value)

    def escrow_curits(self, value: float) -> bool:
        """Escrow a positive value of curits in order to be able to issue nomins against them."""
        if self.curits >= value >= 0:
            self.curits -= value
            self.escrowed_curits += value
            self.model.escrowed_curits += value
            return True
        return False

    def unescrow_curits(self, value: float) -> bool:
        """Unescrow a quantity of curits, if there are not too many issued nomins locking it."""
        if 0 <= value <= self.available_escrowed_curits():
            self.curits += value
            self.escrowed_curits -= value
            self.model.escrowed_curits -= value
            return True
        return False

    def available_escrowed_curits(self) -> float:
        """Return the quantity of escrowed curits which is not locked by issued nomins. """ \
        """May be negative."""
        return self.escrowed_curits - self.model.nom_to_cur(self.issued_nomins)

    def unavailable_escrowed_curits(self) -> float:
        """Return the quantity of escrowed curits locked by having had nomins issued against it. """ \
        """May be greater than total escrowed curits."""
        return self.model.nom_to_cur(self.issued_nomins)

    def max_issuance_rights(self) -> float:
        """The total quantity of nomins this agent has a right to issue."""
        return self.model.cur_to_nom(self.escrowed_curits) * self.model.utilisation_ratio_max

    def issue_nomins(self, value: float) -> bool:
        """Issue a positive value of nomins against currently escrowed curits, """ \
        """up to the utilisation ratio maximum."""
        remaining = self.max_issuance_rights() - self.issued_nomins
        if 0 <= value <= remaining:
            self.issued_nomins += value
            self.nomins += value
            self.model.nomin_supply += value
            return True
        return False

    def burn_nomins(self, value: float) -> bool:
        """Burn a positive value of issued nomins, which frees up curits."""
        if 0 <= value <= self.nomins and value <= self.issued_nomins:
            self.nomins -= value
            self.issued_nomins -= value
            self.model.nomin_supply -= value
            return True
        return False

    def sell_nomins_for_curits(self, quantity: float) -> Bid:
        price = self.model.nom_cur_market.lowest_ask_price()
        order = self.model.nom_cur_market.buy(quantity/price, self)
        self.orders.add(order)
        return order

    def sell_curits_for_nomins(self, quantity: float) -> Ask:
        order = self.model.nom_cur_market.sell(quantity, self)
        self.orders.add(order)
        return order

    def sell_fiat_for_curits(self, quantity: float) -> Bid:
        price = self.model.fiat_cur_market.lowest_ask_price()
        order = self.model.fiat_cur_market.buy(quantity/price, self)
        self.orders.add(order)
        return order

    def sell_curits_for_fiat(self, quantity: float) -> Ask:
        order = self.model.fiat_cur_market.sell(quantity, self)
        self.orders.add(order)
        return order

    def sell_fiat_for_nomins(self, quantity: float) -> Bid:
        price = self.model.fiat_nom_market.lowest_ask_price()
        order = self.model.fiat_nom_market.buy(quantity/price, self)
        self.orders.add(order)
        return order

    def sell_nomins_for_fiat(self, quantity: float) -> Ask:
        order = self.model.fiat_nom_market.sell(quantity, self)
        self.orders.add(order)
        return order

    def notify_cancelled(self, order: Order) -> None:
        pass

    def step(self) -> None:
        pass

class Banker(MarketPlayer):
    """Wants to buy curits and issue nomins, in order to accrue fees."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name = f"Banker {self.unique_id}"
        self.fiat_curit_order = self.sell_fiat_for_curits(0)
        self.nomin_curit_order = self.sell_nomins_for_curits(0)
        self.rate = random.random() * 0.05

    def step(self) -> None:
        if self.fiat > 0:
            self.fiat_curit_order.cancel()
            fiat = self.model.max_transferrable_fiat(self.fiat)
            self.fiat_curit_order = self.sell_fiat_for_curits(fiat * self.rate)

        if self.nomins > 0:
            self.nomin_curit_order.cancel()
            nomins = self.model.max_transferrable_nomins(self.nomins)
            self.nomin_curit_order = self.sell_nomins_for_curits(nomins)

        if self.curits > 0:
            self.escrow_curits(self.curits)

        issuable = self.max_issuance_rights() - self.issued_nomins
        if issuable > 0:
            self.issue_nomins(issuable)


class Arbitrageur(MarketPlayer):
    """Wants to find arbitrage cycles and exploit them to equalise prices."""
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name = f"Arbitrageur {self.unique_id}"

    def find_cycle(self):
        # The only cycles that exist are NOM -> CUR -> FIAT -> NOM,
        # and its reverse.
        # The bot will act to place orders in all markets at once,
        # if there is an arbitrage opportunity, taking into account
        # the fee rates.

        #ncp = self.model.nom_cur_market.price
        #cfp = 1 / self.model.fiat_cur_market.price
        #fnp = self.model.fiat_nom_market.price

        #if ncp * cfp * fnp > 1:
        #elif ncp * cfp
        pass

    def _forward_best_price_quantities_(self) -> Tuple[float, float, float]:
        """The tuple of the quantities available at the best prices in """ \
        """the forward direction around the arbitrage cycle."""
        ncq = min(sum(b.quantity for b in self.model.nom_cur_market.highest_bids()), self.nomins)
        cfq = min(sum(a.quantity for a in self.model.fiat_cur_market.lowest_asks()), self.curits)
        fnq = min(sum(b.quantity for b in self.model.fiat_nom_market.highest_bids()), self.fiat)
        return (ncq, cfq, fnq)

    def _forward_asset_levels_(self, quantities):
        pass

    def _reverse_best_price_quantities_(self) -> Tuple[float, float, float]:
        """The tuple of the quantities available at the best prices in """ \
        """the reverse direction around the arbitrage cycle."""
        cnq = min(sum(a.quantity for a in self.model.nom_cur_market.lowest_asks()), self.curits)
        nfq = min(sum(a.quantity for a in self.model.fiat_nom_market.lowest_asks()), self.nomins)
        fcq = min(sum(b.quantity for b in self.model.fiat_cur_market.highest_bids()), self.fiat)
        return (cnq, nfq, fcq)

    def _equalise_tokens_(self) -> None:
        pass
