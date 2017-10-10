"""agents.py: Individual agents that will interact with the Havven market."""
from typing import Set, Tuple
import random

from mesa import Agent

import orderbook as ob
import model


class MarketPlayer(Agent):
    """
    A generic agent with a fixed initial wealth in fiat,
      with which it must buy into the market.
    The agent may escrow curits in order to issue nomins,
      and use various strategies in order to trade in the marketplace.
      Its aim is to increase its own wealth.
    """

    def __init__(self, unique_id: int, havven: "model.Havven",
                 fiat: float = 0.0, curits: float = 0.0,
                 nomins: float = 0.0) -> None:
        super().__init__(unique_id, havven)
        self.fiat: float = fiat
        self.curits: float = curits
        self.nomins: float = nomins
        self.escrowed_curits: float = 0.0
        self.issued_nomins: float = 0.0

        self.initial_wealth: float = self.wealth()

        self.orders: Set["ob.LimitOrder"] = set()

    def __str__(self) -> str:
        return self.name

    @property
    def name(self) -> str:
        """Return the name of this object; its type and its unique id."""
        return f"{self.__class__.__name__} {self.unique_id}"

    def wealth(self) -> float:
        """Return the total wealth of this agent at current fiat prices."""
        return self.model.fiat_value(self.curits + self.escrowed_curits,
                                     self.nomins - self.issued_nomins,
                                     self.fiat)

    def profit(self) -> float:
        """
        Return the total profit accrued over the initial wealth.
        May be negative.
        """
        return self.wealth() - self.initial_wealth

    def profit_fraction(self) -> float:
        """
        Return profit accrued as a fraction of initial wealth.
        May be negative.
        """
        if self.initial_wealth != 0:
            return self.profit() / self.initial_wealth
        else:
            return 0

    def transfer_fiat_to(self, recipient: "MarketPlayer",
                         value: float) -> bool:
        """
        Transfer a positive value of fiat to the recipient,
        if balance is sufficient. Return True on success.
        """
        return self.model.transfer_fiat(self, recipient, value)

    def transfer_curits_to(self, recipient: "MarketPlayer",
                           value: float) -> bool:
        """
        Transfer a positive value of curits to the recipient,
        if balance is sufficient. Return True on success.
        """
        return self.model.transfer_curits(self, recipient, value)

    def transfer_nomins_to(self, recipient: "MarketPlayer",
                           value: float) -> bool:
        """
        Transfer a positive value of nomins to the recipient,
        if balance is sufficient. Return True on success.
        """
        return self.model.transfer_nomins(self, recipient, value)

    def escrow_curits(self, value: float) -> bool:
        """
        Escrow a positive value of curits in order to be able to issue
        nomins against them.
        """
        if self.curits >= value >= 0:
            self.curits -= value
            self.escrowed_curits += value
            self.model.escrowed_curits += value
            return True
        return False

    def unescrow_curits(self, value: float) -> bool:
        """
        Unescrow a quantity of curits, if there are not too many
        issued nomins locking it.
        """
        if 0 <= value <= self.available_escrowed_curits():
            self.curits += value
            self.escrowed_curits -= value
            self.model.escrowed_curits -= value
            return True
        return False

    def available_escrowed_curits(self) -> float:
        """
        Return the quantity of escrowed curits which is not
        locked by issued nomins. May be negative.
        """
        return self.escrowed_curits - self.model.nom_to_cur(self.issued_nomins)

    def unavailable_escrowed_curits(self) -> float:
        """
        Return the quantity of locked escrowed curits,
          having had nomins issued against it.
        May be greater than total escrowed curits.
        """
        return self.model.nom_to_cur(self.issued_nomins)

    def max_issuance_rights(self) -> float:
        """The total quantity of nomins this agent has a right to issue."""
        return self.model.cur_to_nom(self.escrowed_curits) * \
            self.model.utilisation_ratio_max

    def issue_nomins(self, value: float) -> bool:
        """
        Issue a positive value of nomins against currently escrowed curits,
          up to the utilisation ratio maximum.
        """
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

    def sell_nomins_for_curits(self, quantity: float) -> "ob.Bid":
        """Sell a quantity of nomins in to buy curits."""
        price = self.model.cur_nom_market.lowest_ask_price()
        order = self.model.cur_nom_market.buy(quantity/price, self)
        return order

    def sell_curits_for_nomins(self, quantity: float) -> "ob.Ask":
        """Sell a quantity of curits in to buy nomins."""
        order = self.model.cur_nom_market.sell(quantity, self)
        return order

    def sell_fiat_for_curits(self, quantity: float) -> "ob.Bid":
        """Sell a quantity of fiat in to buy curits."""
        price = self.model.cur_fiat_market.lowest_ask_price()
        order = self.model.cur_fiat_market.buy(quantity/price, self)
        return order

    def sell_curits_for_fiat(self, quantity: float) -> "ob.Ask":
        """Sell a quantity of curits in to buy fiat."""
        order = self.model.cur_fiat_market.sell(quantity, self)
        return order

    def sell_fiat_for_nomins(self, quantity: float) -> "ob.Bid":
        """Sell a quantity of fiat in to buy nomins."""
        price = self.model.nom_fiat_market.lowest_ask_price()
        order = self.model.nom_fiat_market.buy(quantity/price, self)
        return order

    def sell_nomins_for_fiat(self, quantity: float) -> "ob.Ask":
        """Sell a quantity of nomins in to buy fiat."""
        order = self.model.nom_fiat_market.sell(quantity, self)
        return order

    def place_curits_fiat_bid(self, quantity: float, rate: float) -> "ob.Bid":
        """place a bid for quantity curits, at a given rate of fiat"""
        order: "ob.Bid" = self.model.cur_fiat_market.bid(rate, quantity, self)
        return order

    def place_curits_fiat_ask(self, quantity: float, rate: float) -> "ob.Ask":
        """place an ask for fiat with quantity curits,
        at a given rate of fiat"""
        order: "ob.Ask" = self.model.cur_fiat_market.ask(rate, quantity, self)
        return order

    def place_nomins_fiat_bid(self, quantity: float, rate: float) -> "ob.Bid":
        """place a bid for quantity nomins, at a given rate of fiat"""
        order: "ob.Bid" = self.model.nom_fiat_market.bid(rate, quantity, self)
        return order

    def place_nomins_fiat_ask(self, quantity: float, rate: float) -> "ob.Ask":
        """place an ask for fiat with quantity nomins,
        at a given rate of fiat"""
        order: "ob.Ask" = self.model.nom_fiat_market.ask(rate, quantity, self)
        return order

    def place_curits_nomins_bid(self, quantity: float,
                                rate: float) -> "ob.Bid":
        """place a bid for quantity curits, at a given rate of nomins"""
        order: "ob.Bid" = self.model.cur_nom_market.bid(rate, quantity, self)
        return order

    def place_curits_nomins_ask(self, quantity: float,
                                rate: float) -> "ob.Ask":
        """place an ask for curits with quantity nomins,
        at a given rate of curits"""
        order: "ob.Ask" = self.model.cur_nom_market.ask(rate, quantity, self)
        return order

    def notify_cancelled(self, order: "ob.LimitOrder") -> None:
        """Notify this agent that its order was cancelled."""
        pass

    def notify_filled(self, order: "ob.LimitOrder") -> None:
        """Notify this agent that its order was filled."""
        pass

    def step(self) -> None:
        pass

class Banker(MarketPlayer):
    """Wants to buy curits and issue nomins, in order to accrue fees."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fiat_curit_order = None
        self.nomin_curit_order = None
        self.rate = random.random() * 0.05

    def step(self) -> None:
        if self.fiat > 0:
            if self.fiat_curit_order:
                self.fiat_curit_order.cancel()
            fiat = self.model.max_transferrable_fiat(self.fiat)
            self.fiat_curit_order = self.sell_fiat_for_curits(fiat * self.rate)

        if self.nomins > 0:
            if self.nomin_curit_order:
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

    def step(self) -> None:
        """Find an exploitable arbitrage cycle."""
        # The only cycles that exist are CUR -> FIAT -> NOM -> CUR,
        # its rotations, and the reverse cycles.
        # The bot will act to place orders in all markets at once,
        # if there is an arbitrage opportunity, taking into account
        # the fee rates.

        if self._forward_multiple_() > 1:
            # Trade in the forward direction
            # TODO: work out which rotation of this cycle would be the least wasteful
            # cur -> fiat -> nom -> cur
            #cf_price = self.model.cur_fiat_market.highest_bid_price()
            fn_price = 1.0 / self.model.nom_fiat_market.lowest_ask_price()
            nc_price = 1.0 / self.model.cur_nom_market.lowest_ask_price()

            cf_qty = sum(b.quantity for b in self.model.cur_fiat_market.highest_bids())
            fn_qty = sum(a.quantity for a in self.model.nom_fiat_market.lowest_asks())
            nc_qty = sum(a.quantity for a in self.model.cur_nom_market.lowest_asks())

            c_qty = min(self.curits, cf_qty)
            self.sell_curits_for_fiat(c_qty)

            f_qty = min(self.fiat, fn_qty * fn_price)
            self.sell_fiat_for_curits(f_qty)

            n_qty = min(self.nomins, nc_qty * nc_price)
            self.sell_nomins_for_curits(n_qty)

        elif self._reverse_multiple_() > 1:
            # Trade in the reverse direction
            # cur -> nom -> fiat -> cur
            #cn_price = self.model.cur_nom_market.highest_bid_price()
            #nf_price = self.model.nom_fiat_market.highest_bid_price()
            fc_price = 1.0 / self.model.cur_fiat_market.lowest_ask_price()

            cn_qty = sum(b.quantity for b in self.model.cur_nom_market.highest_bids())
            nf_qty = sum(b.quantity for b in self.model.nom_fiat_market.highest_bids())
            fc_qty = sum(a.quantity for a in self.model.cur_fiat_market.lowest_asks())

            c_qty = min(self.curits, cn_qty)
            self.sell_curits_for_nomins(c_qty)

            n_qty = min(self.nomins, nf_qty)
            self.sell_nomins_for_fiat(n_qty)

            f_qty = min(self.fiat, fc_qty * fc_price)
            self.sell_nomins_for_curits(n_qty)

    def _cycle_fee_rate_(self) -> float:
        """Divide by this fee rate to determine losses after one traversal of an arbitrage cycle."""
        return (1 + self.model.nom_transfer_fee_rate) * \
               (1 + self.model.cur_transfer_fee_rate) * \
               (1 + self.model.fiat_transfer_fee_rate)

    def _forward_multiple_no_fees_(self) -> float:
        """
        The value multiple after one forward arbitrage cycle, neglecting fees.
        """
        # cur -> fiat -> nom -> cur
        return self.model.cur_fiat_market.highest_bid_price() / \
               (self.model.nom_fiat_market.lowest_ask_price() * self.model.cur_nom_market.lowest_ask_price())

    def _reverse_multiple_no_fees_(self) -> float:
        """
        The value multiple after one reverse arbitrage cycle, neglecting fees.
        """
        # cur -> nom -> fiat -> cur
        return self.model.cur_nom_market.highest_bid_price() * self.model.nom_fiat_market.highest_bid_price() / \
               self.model.cur_fiat_market.lowest_ask_price()

    def _forward_multiple_(self) -> float:
        """The return after one forward arbitrage cycle."""
        # Note, this only works because the fees are purely multiplicative.
        return self._forward_multiple_no_fees_() / self._cycle_fee_rate_()

    def _reverse_multiple_(self) -> float:
        """The return after one reverse arbitrage cycle."""
        # As above. If the fees were not just levied as percentages this would need to be updated.
        return self._reverse_multiple_no_fees_() / self._cycle_fee_rate_()

    def _equalise_tokens_(self) -> None:
        pass

class Randomizer(MarketPlayer):
    """Places random bids and asks."""
    def step(self) -> None:
        if self.fiat > 0:
            for i in range(10):
                if random.random() > 0.5:
                    self.place_curits_fiat_bid(self.fiat/10,
                        round(random.random(), 3))
                else:
                    self.place_curits_fiat_ask(self.fiat/10,
                        round(1+random.random(), 3))
