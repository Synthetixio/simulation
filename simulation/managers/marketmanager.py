from typing import Optional, Callable
from decimal import Decimal as Dec

import orderbook as ob
import agents as ag

from .havvenmanager import HavvenManager
from .feemanager import FeeManager


class MarketManager:
    """
    Handles all order books, trades, transfers, and conversions.
    """

    def __init__(self, model_manager: HavvenManager, fee_manager: FeeManager) -> None:

        self.model_manager = model_manager
        self.fee_manager = fee_manager

        # Order books
        # If a book is X_Y_market, then X is the base currency,
        #   Y is the quote currency.
        # That is, buyers hold Y and sellers hold X.
        self.curit_nomin_market = ob.OrderBook(
            model_manager, "curits", "nomins", self.curit_nomin_match,
            self.fee_manager.transferred_nomins_fee,
            self.fee_manager.transferred_curits_fee,
            self.model_manager.match_on_order
        )
        self.curit_fiat_market = ob.OrderBook(
            model_manager, "curits", "fiat", self.curit_fiat_match,
            self.fee_manager.transferred_fiat_fee,
            self.fee_manager.transferred_curits_fee,
            self.model_manager.match_on_order
        )
        self.nomin_fiat_market = ob.OrderBook(
            model_manager, "nomins", "fiat", self.nomin_fiat_match,
            self.fee_manager.transferred_fiat_fee,
            self.fee_manager.transferred_nomins_fee,
            self.model_manager.match_on_order
        )

    def __bid_ask_match__(
            self, bid: "ob.Bid", ask: "ob.Ask",
            bid_success: Callable[["ag.MarketPlayer", Dec, Dec], bool],
            ask_success: Callable[["ag.MarketPlayer", Dec, Dec], bool],
            bid_transfer: Callable[["ag.MarketPlayer", "ag.MarketPlayer", Dec, Dec], bool],
            ask_transfer: Callable[["ag.MarketPlayer", "ag.MarketPlayer", Dec, Dec], bool]
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
        price = HavvenManager.round_decimal(ask.price if ask.time < bid.time else bid.price)
        quantity = HavvenManager.round_decimal(min(ask.quantity, bid.quantity))
        try:
            # only charge a fraction of the fee
            if quantity == ask.quantity:
                ask_fee = HavvenManager.round_decimal(ask.fee)
                bid_fee = HavvenManager.round_decimal(quantity/bid.quantity * bid.fee)
            else:
                bid_fee = HavvenManager.round_decimal(bid.fee)
                ask_fee = HavvenManager.round_decimal(quantity/ask.quantity * ask.fee)
            buy_val = HavvenManager.round_decimal(quantity * price)
        except Exception as e:
            print(bid, ask)
            print(e)
            import time
            time.sleep(100)
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
        ask.update_quantity(HavvenManager.round_decimal(ask.quantity - quantity),
                            HavvenManager.round_decimal(ask_fee))
        bid.update_quantity(HavvenManager.round_decimal(bid.quantity - quantity),
                            HavvenManager.round_decimal(bid_fee))

        return ob.TradeRecord(bid.issuer, ask.issuer,
                              price, quantity, bid_fee, ask_fee)

    def curit_nomin_match(self, bid: "ob.Bid",
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

    def curit_fiat_match(self, bid: "ob.Bid",
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

    def nomin_fiat_match(self, bid: "ob.Bid",
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
                              quantity: Dec, fee: Dec) -> bool:
        """True iff the sender could successfully send a quantity of fiat."""
        return 0 <= quantity + fee <= HavvenManager.round_decimal(sender.fiat)

    def transfer_curits_success(self, sender: "ag.MarketPlayer",
                                quantity: Dec, fee: Dec) -> bool:
        """True iff the sender could successfully send a quantity of curits."""
        return 0 <= quantity + fee <= HavvenManager.round_decimal(sender.curits)

    def transfer_nomins_success(self, sender: "ag.MarketPlayer",
                                quantity: Dec, fee: Dec) -> bool:
        """True iff the sender could successfully send a quantity of nomins."""
        return 0 <= quantity + fee <= HavvenManager.round_decimal(sender.nomins)

    def transfer_fiat(self, sender: "ag.MarketPlayer",
                      recipient: "ag.MarketPlayer", quantity: Dec, fee: Dec) -> bool:
        """
        Transfer a positive quantity of fiat currency from the sender to the
          recipient, if balance is sufficient. Return True on success.
        """
        if self.transfer_fiat_success(sender, quantity, fee):
            sender.fiat -= quantity + fee
            recipient.fiat += quantity
            self.model_manager.fiat += fee
            return True
        return False

    def transfer_curits(self, sender: 'ag.MarketPlayer',
                        recipient: 'ag.MarketPlayer', quantity: Dec, fee: Dec) -> bool:
        """
        Transfer a positive quantity of curits from the sender to the recipient,
          if balance is sufficient. Return True on success.
        """
        if self.transfer_curits_success(sender, quantity, fee):
            sender.curits -= quantity + fee
            recipient.curits += quantity
            self.model_manager.curits += fee
            return True
        return False

    def transfer_nomins(self, sender: 'ag.MarketPlayer',
                        recipient: 'ag.MarketPlayer', quantity: Dec, fee: Dec) -> bool:
        """
        Transfer a positive quantity of nomins from the sender to the recipient,
          if balance is sufficient. Return True on success.
        """
        if self.transfer_nomins_success(sender, quantity, fee):
            sender.nomins -= quantity + fee
            recipient.nomins += quantity
            self.model_manager.nomins += fee
            return True
        return False

    def curits_to_nomins(self, quantity: Dec) -> Dec:
        """Convert a quantity of curits to its equivalent quantity in nomins."""
        return quantity * self.curit_nomin_market.price
        # The following fixes an interesting feedback loop related to nomin issuance rights
        # Hopefully unbreaking arbitrage will fix that, however.
        # return (quantity * self.curit_fiat_market.price) / self.nomin_fiat_market.price

    def curits_to_fiat(self, quantity: Dec) -> Dec:
        """Convert a quantity of curits to its equivalent quantity in fiat."""
        return quantity * self.curit_fiat_market.price

    def nomins_to_curits(self, quantity: Dec) -> Dec:
        """Convert a quantity of nomins to its equivalent quantity in curits."""
        return quantity / self.curit_nomin_market.price
        # The following fixes an interesting feedback loop related to nomin issuance rights
        # Hopefully unbreaking arbitrage will fix that, however.
        # return (quantity * self.nomin_fiat_market.price) / self.curit_fiat_market.price

    def nomins_to_fiat(self, quantity: Dec) -> Dec:
        """Convert a quantity of nomins to its equivalent quantity in fiat."""
        return quantity * self.nomin_fiat_market.price

    def fiat_to_curits(self, quantity: Dec) -> Dec:
        """Convert a quantity of fiat to its equivalent quantity in curits."""
        return quantity / self.curit_fiat_market.price

    def fiat_to_nomins(self, quantity: Dec) -> Dec:
        """Convert a quantity of fiat to its equivalent quantity in nomins."""
        return quantity / self.nomin_fiat_market.price
