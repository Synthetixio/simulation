from typing import Set

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

    def reset_initial_wealth(self) -> float:
        """Reset this agent's initial wealth to the current wealth, returning the old value."""
        old = self.initial_wealth
        self.initial_wealth = self.wealth()
        return old

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
        return self.model.trade_manager.transfer_fiat(self, recipient, value)

    def transfer_curits_to(self, recipient: "MarketPlayer",
                           value: float) -> bool:
        """
        Transfer a positive value of curits to the recipient,
        if balance is sufficient. Return True on success.
        """
        return self.model.trade_manager.transfer_curits(self, recipient, value)

    def transfer_nomins_to(self, recipient: "MarketPlayer",
                           value: float) -> bool:
        """
        Transfer a positive value of nomins to the recipient,
        if balance is sufficient. Return True on success.
        """
        return self.model.trade_manager.transfer_nomins(self, recipient, value)

    def escrow_curits(self, value: float) -> bool:
        """
        Escrow a positive value of curits in order to be able to issue
        nomins against them.
        """
        if self.curits >= value >= 0:
            self.curits -= value
            self.escrowed_curits += value
            self.model.manager.escrowed_curits += value
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
            self.model.manager.escrowed_curits -= value
            return True
        return False

    def available_escrowed_curits(self) -> float:
        """
        Return the quantity of escrowed curits which is not
        locked by issued nomins. May be negative.
        """
        return self.escrowed_curits - self.model.trade_manager.nom_to_cur(self.issued_nomins)

    def unavailable_escrowed_curits(self) -> float:
        """
        Return the quantity of locked escrowed curits,
          having had nomins issued against it.
        May be greater than total escrowed curits.
        """
        return self.model.trade_manager.nom_to_cur(self.issued_nomins)

    def max_issuance_rights(self) -> float:
        """The total quantity of nomins this agent has a right to issue."""
        return self.model.trade_manager.cur_to_nom(self.escrowed_curits) * \
            self.model.manager.utilisation_ratio_max

    def issue_nomins(self, value: float) -> bool:
        """
        Issue a positive value of nomins against currently escrowed curits,
          up to the utilisation ratio maximum.
        """
        remaining = self.max_issuance_rights() - self.issued_nomins
        if 0 <= value <= remaining:
            self.issued_nomins += value
            self.nomins += value
            self.model.manager.nomin_supply += value
            return True
        return False

    def burn_nomins(self, value: float) -> bool:
        """Burn a positive value of issued nomins, which frees up curits."""
        if 0 <= value <= self.nomins and value <= self.issued_nomins:
            self.nomins -= value
            self.issued_nomins -= value
            self.model.manager.nomin_supply -= value
            return True
        return False

    def sell_nomins_for_curits(self, quantity: float) -> "ob.Bid":
        """Sell a quantity of nomins in to buy curits."""
        price = self.model.trade_manager.cur_nom_market.lowest_ask_price()
        return self.model.trade_manager.cur_nom_market.buy(quantity/price, self)

    def sell_curits_for_nomins(self, quantity: float) -> "ob.Ask":
        """Sell a quantity of curits in to buy nomins."""
        return self.model.trade_manager.cur_nom_market.sell(quantity, self)

    def sell_fiat_for_curits(self, quantity: float) -> "ob.Bid":
        """Sell a quantity of fiat in to buy curits."""
        price = self.model.trade_manager.cur_fiat_market.lowest_ask_price()
        return self.model.trade_manager.cur_fiat_market.buy(quantity/price, self)

    def sell_curits_for_fiat(self, quantity: float) -> "ob.Ask":
        """Sell a quantity of curits in to buy fiat."""
        return self.model.trade_manager.cur_fiat_market.sell(quantity, self)

    def sell_fiat_for_nomins(self, quantity: float) -> "ob.Bid":
        """Sell a quantity of fiat in to buy nomins."""
        price = self.model.trade_manager.nom_fiat_market.lowest_ask_price()
        return self.model.trade_manager.nom_fiat_market.buy(quantity/price, self)

    def sell_nomins_for_fiat(self, quantity: float) -> "ob.Ask":
        """Sell a quantity of nomins in to buy fiat."""
        return self.model.trade_manager.nom_fiat_market.sell(quantity, self)

    def place_curits_fiat_bid(self, quantity: float, price: float) -> "ob.Bid":
        """Place a bid for quantity curits, at a given price in fiat."""
        return self.model.trade_manager.cur_fiat_market.bid(price, quantity, self)

    def place_curits_fiat_ask(self, quantity: float, price: float) -> "ob.Ask":
        """Place an ask for fiat with quantity curits, at a given price in fiat."""
        return self.model.trade_manager.cur_fiat_market.ask(price, quantity, self)

    def place_nomins_fiat_bid(self, quantity: float, price: float) -> "ob.Bid":
        """Place a bid for quantity nomins, at a given price in fiat."""
        return self.model.trade_manager.nom_fiat_market.bid(price, quantity, self)

    def place_nomins_fiat_ask(self, quantity: float, price: float) -> "ob.Ask":
        """Place an ask for fiat with quantity nomins, at a given price in fiat."""
        return self.model.trade_manager.nom_fiat_market.ask(price, quantity, self)

    def place_curits_nomins_bid(self, quantity: float, price: float) -> "ob.Bid":
        """Place a bid for quantity curits, at a given price in nomins."""
        return self.model.trade_manager.cur_nom_market.bid(price, quantity, self)

    def place_curits_nomins_ask(self, quantity: float, price: float) -> "ob.Ask":
        """place an ask for curits with quantity nomins, at a given price in curits."""
        return self.model.trade_manager.cur_nom_market.ask(price, quantity, self)

    def notify_cancelled(self, order: "ob.LimitOrder") -> None:
        """Notify this agent that its order was cancelled."""
        pass

    def notify_filled(self, order: "ob.LimitOrder") -> None:
        """Notify this agent that its order was filled."""
        pass

    def step(self) -> None:
        pass
