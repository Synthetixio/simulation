"""
Classes for holding onto values and functions for the model and agents
"""

from config import FeeConfig
from typing import List, Optional, Callable

import orderbook as ob
import agents as ag


class HavvenManager:
    """
    Class to hold Havven's model variables
    """

    def __init__(self, num_agents: int,
                 utilisation_ratio_max: float = 1.0,
                 match_on_order: bool = True) -> None:
        # Add the market participants
        self.num_agents: int = num_agents

        # Utilisation Ratio maximum (between 0 and 1)
        self.utilisation_ratio_max: float = utilisation_ratio_max

        # If true, match orders whenever an order is posted,
        #   otherwise do so at the end of each period
        self.match_on_order: bool = match_on_order

        # Money Supply
        self.curit_supply: float = 10.0 ** 9
        self.nomin_supply: float = 0.0
        self.escrowed_curits: float = 0.0

        # Havven's own capital supplies
        self.curits: float = self.curit_supply
        self.nomins: float = 0.0
        self.fiat: float = 0.0


class FeeManager:
    """
    Class to handle fee calculation
    """

    def __init__(self, model_manager: "HavvenManager") -> None:
        self.fees_distributed: float = 0.0
        self.model_manager = model_manager

    def max_transferrable_fiat(self, principal: float) -> float:
        """
        A user can transfer less than their total balance when fees are
          taken into account.
        """
        return principal / (1 + FeeConfig.fiat_transfer_fee_rate)

    def max_transferrable_curits(self, principal: float) -> float:
        """
        A user can transfer less than their total balance when fees are
          taken into account.
        """
        return principal / (1 + FeeConfig.cur_transfer_fee_rate)

    def max_transferrable_nomins(self, principal: float) -> float:
        """
        A user can transfer less than their total balance when fees are
          taken into account.
        """
        return principal / (1 + FeeConfig.nom_transfer_fee_rate)

    def transfer_fiat_fee(self, value: float) -> float:
        """Return the fee charged for transferring a value of fiat."""
        return value * FeeConfig.fiat_transfer_fee_rate

    def transfer_curits_fee(self, value: float) -> float:
        """Return the fee charged for transferring a value of curits."""
        return value * FeeConfig.cur_transfer_fee_rate

    def transfer_nomins_fee(self, value: float) -> float:
        """Return the fee charged for transferring a value of nomins."""
        return value * FeeConfig.nom_transfer_fee_rate

    def distribute_fees(self, schedule_agents: List["ag.MarketPlayer"]) -> None:
        """Distribute currently held nomins to holders of curits."""
        # Different fee modes:
        #  * distributed by held curits
        # TODO: * distribute by escrowed curits
        # TODO: * distribute by issued nomins
        # TODO: * distribute by motility

        for agent in schedule_agents:
            if self.model_manager.nomins == 0:
                break
            qty = min(agent.issued_nomins / self.model_manager.nomins, self.model_manager.nomins)
            agent.nomins += qty
            self.model_manager.nomins -= qty
            self.fees_distributed += qty

    def get_bid_fee(self, base: str, quote: str, quantity: float, rate: float) -> float:
        """
        Return the fee to place a bid on base-quote market at a given quantity/rate
        """
        if quote == "FIAT":
            return self.transfer_fiat_fee(quantity)
        elif quote == "NOM":
            return self.transfer_nomins_fee(quantity)
        elif quote == "CUR":
            return self.transfer_curits_fee(quantity)
        raise Exception(f"Market quote {quote} isn't in [FIAT,NOM,CUR]")

    def get_ask_fee(self, base: str, quote: str, quantity: float, rate: float) -> float:
        """
        Return the fee to place an ask on base-quote market at a given quantity/rate
        """
        if base == "FIAT":
            return self.transfer_fiat_fee(quantity)
        elif base == "NOM":
            return self.transfer_nomins_fee(quantity)
        elif base == "CUR":
            return self.transfer_curits_fee(quantity)
        raise Exception(f"Market base {base} isn't in [FIAT,NOM,CUR]")


class TradeManager:
    """
    Class to handle all trades and order books
    """

    def __init__(self, model_manager: "HavvenManager", fee_manager: "FeeManager") -> None:

        self.model_manager = model_manager
        self.fee_manager = fee_manager

        # Order books
        # If a book is X_Y_market, then X is the base currency,
        #   Y is the quote currency.
        # That is, buyers hold Y and sellers hold X.
        self.cur_nom_market: ob.OrderBook = ob.OrderBook(
            self.fee_manager, "CUR", "NOM", self.cur_nom_match, self.model_manager.match_on_order
        )
        self.cur_fiat_market: ob.OrderBook = ob.OrderBook(
            self.fee_manager, "CUR", "FIAT", self.cur_fiat_match, self.model_manager.match_on_order
        )
        self.nom_fiat_market: ob.OrderBook = ob.OrderBook(
            self.fee_manager, "NOM", "FIAT", self.nom_fiat_match, self.model_manager.match_on_order
        )

    def __bid_ask_match__(
            self, bid: "ob.Bid", ask: "ob.Ask",
            bid_success: Callable[["ag.MarketPlayer", float, float], bool],
            ask_success: Callable[["ag.MarketPlayer", float, float], bool],
            bid_transfer: Callable[["ag.MarketPlayer", "ag.MarketPlayer", float, float], bool],
            ask_transfer: Callable[["ag.MarketPlayer", "ag.MarketPlayer", float, float], bool]
    ) -> Optional["ob.TradeRecord"]:
        """
        If possible, match the given bid and ask, with the given transfer
          and success functions.
        Cancel any orders which an agent cannot afford to service.
        Return a TradeRecord object if the match succeeded, otherwise None.
        """

        if ask.price > bid.price:
            return None

        # Price will be favourable to whoever went second.
        # The earlier poster trades at their posted price,
        #   while the later poster transacts at a price no worse than posted;
        #   they may do better.
        price = ask.price if ask.time < bid.time else bid.price
        quantity = min(ask.quantity, bid.quantity)

        # only charge a fraction of the fee
        if quantity == ask.quantity:
            ask_fee = ask.fee
            bid_fee = quantity/bid.quantity * bid.fee
        else:
            bid_fee = bid.fee
            ask_fee = quantity/ask.quantity * ask.fee
        buy_val = quantity * price

        # Only perform the actual transfer if it would be successful.
        # Cancel any orders that would not succeed.
        fail = False
        if not bid_success(bid.issuer, buy_val, bid_fee):
            bid.cancel()
            fail = True
        if not ask_success(ask.issuer, quantity, ask_fee):
            ask.cancel()
            fail = True
        if fail:
            return None

        # Perform the actual transfers.
        # We have already checked above if these would succeed.
        ask_transfer(ask.issuer, bid.issuer, quantity, ask_fee)
        bid_transfer(bid.issuer, ask.issuer, buy_val, bid_fee)

        # Update the orders, cancelling any with 0 remaining quantity.
        ask.update_quantity(ask.quantity - quantity, ask_fee)
        bid.update_quantity(bid.quantity - quantity, bid_fee)

        return ob.TradeRecord(bid.issuer, ask.issuer, price, quantity)

    def cur_nom_match(self, bid: "ob.Bid",
                      ask: "ob.Ask") -> Optional["ob.TradeRecord"]:
        """
        Buyer offers nomins in exchange for curits from the seller.
        Return a TradeRecord object if the match succeeded, otherwise None.
        """
        return self.__bid_ask_match__(bid, ask,
                                      self.transfer_nomins_success,
                                      self.transfer_curits_success,
                                      self.transfer_nomins,
                                      self.transfer_curits)

    def cur_fiat_match(self, bid: "ob.Bid",
                       ask: "ob.Ask") -> Optional["ob.TradeRecord"]:
        """
        Buyer offers fiat in exchange for curits from the seller.
        Return a TradeRecord object if the match succeeded, otherwise None.
        """
        return self.__bid_ask_match__(bid, ask,
                                      self.transfer_fiat_success,
                                      self.transfer_curits_success,
                                      self.transfer_fiat,
                                      self.transfer_curits)

    def nom_fiat_match(self, bid: "ob.Bid",
                       ask: "ob.Ask") -> Optional["ob.TradeRecord"]:
        """
        Buyer offers fiat in exchange for nomins from the seller.
        Return a TradeRecord object if the match succeeded, otherwise None.
        """
        return self.__bid_ask_match__(bid, ask,
                                      self.transfer_fiat_success,
                                      self.transfer_nomins_success,
                                      self.transfer_fiat,
                                      self.transfer_nomins)

    def transfer_fiat_success(self, sender: "ag.MarketPlayer",
                              value: float, fee: float) -> bool:
        """True iff the sender could successfully send a value of fiat."""
        return 0 <= value + fee <= sender.fiat

    def transfer_curits_success(self, sender: "ag.MarketPlayer",
                                value: float, fee: float) -> bool:
        """True iff the sender could successfully send a value of curits."""
        return 0 <= value + fee <= sender.curits

    def transfer_nomins_success(self, sender: "ag.MarketPlayer",
                                value: float, fee: float) -> bool:
        """True iff the sender could successfully send a value of nomins."""
        return 0 <= value + fee <= sender.nomins

    def transfer_fiat(self, sender: "ag.MarketPlayer",
                      recipient: "ag.MarketPlayer", value: float, fee: float) -> bool:
        """
        Transfer a positive value of fiat currency from the sender to the
          recipient, if balance is sufficient. Return True on success.
        """
        if self.transfer_fiat_success(sender, value, fee):
            sender.fiat -= value + fee
            recipient.fiat += value
            self.model_manager.fiat += fee
            return True
        return False

    def transfer_curits(self, sender: 'ag.MarketPlayer',
                        recipient: 'ag.MarketPlayer', value: float, fee: float) -> bool:
        """
        Transfer a positive value of curits from the sender to the recipient,
          if balance is sufficient. Return True on success.
        """
        if self.transfer_curits_success(sender, value, fee):
            sender.curits -= value + fee
            recipient.curits += value
            self.model_manager.curits += fee
            return True
        return False

    def transfer_nomins(self, sender: 'ag.MarketPlayer',
                        recipient: 'ag.MarketPlayer', value: float, fee: float) -> bool:
        """
        Transfer a positive value of nomins from the sender to the recipient,
          if balance is sufficient. Return True on success.
        """
        if self.transfer_nomins_success(sender, value, fee):
            sender.nomins -= value + fee
            recipient.nomins += value
            self.model_manager.nomins += fee
            return True
        return False

    @property
    def curit_fiat_price(self) -> float:
        """Return the current curit price in fiat per token."""
        return self.cur_fiat_market.price

    @property
    def nomin_fiat_price(self) -> float:
        """Return the current nomin price in fiat per token."""
        return self.nom_fiat_market.price

    @property
    def curit_nomin_price(self) -> float:
        """Return the current curit price in nomins per token."""
        return self.cur_nom_market.price

    def cur_to_nom(self, value: float) -> float:
        """Convert a quantity of curits to its equivalent value in nomins."""
        return value * self.curit_nomin_price

    def cur_to_fiat(self, value: float) -> float:
        """Convert a quantity of curits to its equivalent value in fiat."""
        return value * self.curit_fiat_price

    def nom_to_cur(self, value: float) -> float:
        """Convert a quantity of nomins to its equivalent value in curits."""
        return value / self.curit_nomin_price

    def nom_to_fiat(self, value: float) -> float:
        """Convert a quantity of nomins to its equivalent value in fiat."""
        return value * self.nomin_fiat_price

    def fiat_to_cur(self, value: float) -> float:
        """Convert a quantity of fiat to its equivalent value in curits."""
        return value / self.curit_fiat_price

    def fiat_to_nom(self, value: float) -> float:
        """Convert a quantity of fiat to its equivalent value in nomins."""
        return value / self.nomin_fiat_price
