from config import FeeConfig


class TradeManager:
    def __init__(self):
        # Order books
        # If a book is X_Y_market, then X is the base currency,
        #   Y is the quote currency.
        # That is, buyers hold Y and sellers hold X.
        self.cur_nom_market: ob.OrderBook = ob.OrderBook(
            "CUR", "NOM", self.cur_nom_match, self.match_on_order
        )
        self.cur_fiat_market: ob.OrderBook = ob.OrderBook(
            "CUR", "FIAT", self.cur_fiat_match, self.match_on_order
        )
        self.nom_fiat_market: ob.OrderBook = ob.OrderBook(
            "NOM", "FIAT", self.nom_fiat_match, self.match_on_order
        )

    def __bid_ask_match__(
            self, bid: ob.Bid, ask: ob.Ask,
            bid_success: TransferTest, ask_success: TransferTest,
            bid_transfer: TransferFunction,
            ask_transfer: TransferFunction) -> Optional[ob.TradeRecord]:
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
        buy_val = quantity*price

        # Only perform the actual transfer if it would be successful.
        # Cancel any orders that would not succeed.
        fail = False
        if not bid_success(bid.issuer, buy_val):
            bid.cancel()
            fail = True
        if not ask_success(ask.issuer, quantity):
            ask.cancel()
            fail = True
        if fail:
            return None

        # Perform the actual transfers.
        # We have already checked above if these would succeed.
        bid_transfer(bid.issuer, ask.issuer, buy_val)
        ask_transfer(ask.issuer, bid.issuer, quantity)

        # Update the orders, cancelling any with 0 remaining quantity.
        ask.update_quantity(ask.quantity - quantity)
        bid.update_quantity(bid.quantity - quantity)

        return ob.TradeRecord(bid.issuer, ask.issuer, price, quantity)

    def cur_nom_match(self, bid: ob.Bid,
                      ask: ob.Ask) -> Optional[ob.TradeRecord]:
        """
        Buyer offers nomins in exchange for curits from the seller.
        Return a TradeRecord object if the match succeeded, otherwise None.
        """
        return self.__bid_ask_match__(bid, ask,
                                      self.transfer_nomins_success,
                                      self.transfer_curits_success,
                                      self.transfer_nomins,
                                      self.transfer_curits)

    def cur_fiat_match(self, bid: ob.Bid,
                       ask: ob.Ask) -> Optional[ob.TradeRecord]:
        """
        Buyer offers fiat in exchange for curits from the seller.
        Return a TradeRecord object if the match succeeded, otherwise None.
        """
        return self.__bid_ask_match__(bid, ask,
                                      self.transfer_fiat_success,
                                      self.transfer_curits_success,
                                      self.transfer_fiat,
                                      self.transfer_curits)

    def nom_fiat_match(self, bid: ob.Bid,
                       ask: ob.Ask) -> Optional[ob.TradeRecord]:
        """
        Buyer offers fiat in exchange for nomins from the seller.
        Return a TradeRecord object if the match succeeded, otherwise None.
        """
        return self.__bid_ask_match__(bid, ask,
                                      self.transfer_fiat_success,
                                      self.transfer_nomins_success,
                                      self.transfer_fiat,
                                      self.transfer_nomins)

    def transfer_fiat_success(self, sender: ag.MarketPlayer,
                              value: float) -> bool:
        """True iff the sender could successfully send a value of fiat."""
        return 0 <= value + self.transfer_fiat_fee(value) <= sender.fiat

    def transfer_curits_success(self, sender: ag.MarketPlayer,
                                value: float) -> bool:
        """True iff the sender could successfully send a value of curits."""
        return 0 <= value + self.transfer_curits_fee(value) <= sender.curits

    def transfer_nomins_success(self, sender: ag.MarketPlayer,
                                value: float) -> bool:
        """True iff the sender could successfully send a value of nomins."""
        return 0 <= value + self.transfer_nomins_fee(value) <= sender.nomins

    def transfer_fiat(self, sender: ag.MarketPlayer,
                      recipient: ag.MarketPlayer, value: float) -> bool:
        """
        Transfer a positive value of fiat currency from the sender to the
          recipient, if balance is sufficient. Return True on success.
        """
        if self.transfer_fiat_success(sender, value):
            fee = self.transfer_fiat_fee(value)
            sender.fiat -= value + fee
            recipient.fiat += value
            self.fiat += fee
            return True
        return False

    def transfer_curits(self, sender: ag.MarketPlayer,
                        recipient: ag.MarketPlayer, value: float) -> bool:
        """
        Transfer a positive value of curits from the sender to the recipient,
          if balance is sufficient. Return True on success.
        """
        if self.transfer_curits_success(sender, value):
            fee = self.transfer_curits_fee(value)
            sender.curits -= value + fee
            recipient.curits += value
            self.curits += fee
            return True
        return False

    def transfer_nomins(self, sender: ag.MarketPlayer,
                        recipient: ag.MarketPlayer, value: float) -> bool:
        """
        Transfer a positive value of nomins from the sender to the recipient,
          if balance is sufficient. Return True on success.
        """
        if self.transfer_nomins_success(sender, value):
            fee = self.transfer_nomins_fee(value)
            sender.nomins -= value + fee
            recipient.nomins += value
            self.nomins += fee
            return True
        return False

class FeeManager:
    """
    Class to handle fee calculation
    """
    def __init__(self, model_settings: "HavvenConfig"):
        self.fees_distributed: float = 0.0
        self.model_settings = model_settings

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

    def cur_to_nom(self, value: float) -> float:
        """Convert a quantity of curits to its equivalent value in nomins."""
        return (value * self.curit_price) / self.nomin_price

    def cur_to_fiat(self, value: float) -> float:
        """Convert a quantity of curits to its equivalent value in fiat."""
        return value * self.curit_price

    def nom_to_cur(self, value: float) -> float:
        """Convert a quantity of nomins to its equivalent value in curits."""
        return (value * self.nomin_price) / self.curit_price

    def nom_to_fiat(self, value: float) -> float:
        """Convert a quantity of nomins to its equivalent value in fiat."""
        return value * self.nomin_price

    def fiat_to_cur(self, value: float) -> float:
        """Convert a quantity of fiat to its equivalent value in curits."""
        return value / self.curit_price

    def fiat_to_nom(self, value: float) -> float:
        """Convert a quantity of fiat to its equivalent value in nomins."""
        return value / self.nomin_price