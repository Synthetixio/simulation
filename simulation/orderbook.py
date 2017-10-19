"""orderbook: an order book for trading in a market."""

from typing import Iterable, Callable, List, Optional
from itertools import takewhile
from decimal import Decimal as Dec

# We need a fast ordered data structure to support efficient insertion and deletion of orders.
from sortedcontainers import SortedListWithKey, SortedDict

import agents as ag

from managers import HavvenManager

class LimitOrder:
    """
    A single limit order, including price, quantity, the issuer, and orderbook it belongs to.
    """
    def __init__(self, price: Dec, time: int, quantity: Dec, fee: Dec,
                 issuer: "ag.MarketPlayer", book: "OrderBook") -> None:
        self.price = HavvenManager.round_decimal(price)
        """Quoted currency per unit of base currency."""

        self.fee = HavvenManager.round_decimal(fee)
        """An extra fee charged on top of the face value of the order."""

        self.time = time
        """The time this order was created, or last modified."""

        self.quantity = HavvenManager.round_decimal(quantity)
        """Denominated in the base currency."""

        self.issuer = issuer
        """The player which issued this order."""

        self.book = book
        """The order book this order is listed on."""

        self.active = self.quantity > 0
        """Whether the order is actively listed or not."""

    def cancel(self) -> None:
        """Remove this order from the issuer and the order book if it's active."""
        pass

    def update_price(self, price: Dec,
                     fee: Optional[Dec] = None) -> None:
        """
        Update this order's price, updating its timestamp, possibly reordering its order book.
        If fee is not None, set the fee directly, otherwise recompute it.
        """
        pass

    def update_quantity(self, quantity: Dec,
                        fee: Optional[Dec] = None) -> None:
        """
        Update the quantity of this order, updating its timestamp, cancelling if not positive.
        If fee is not None, set the fee directly, otherwise recompute it.
        """
        pass

    def __str__(self) -> str:
        return f"{self.quantity}@{self.price} f:{self.fee} " \
               f"({self.book.name if self.book else None}) " \
               f"t:{self.time} by {self.issuer}"


class Bid(LimitOrder):
    """A bid order. Instantiating one of these will automatically add it to its order book."""
    def __init__(self, price: Dec, quantity: Dec, fee: Dec,
                 issuer: "ag.MarketPlayer", book: "OrderBook") -> None:
        super().__init__(price, book.time, quantity, fee, issuer, book)
        # Note that the bid will not be active if quantity is not positive.
        self.book._add_new_bid_(self)

    @classmethod
    def comparator(cls, bid: "Bid"):
        """Bids are sorted first by descending price and then by ascending time."""
        return -bid.price, bid.time

    def cancel(self) -> None:
        """Remove this bid from the issuer and the order book if it's active."""
        self.book.cancel_bid(self)

    def update_price(self, price: Dec,
                     fee: Optional[Dec] = None) -> None:
        """
        Update this bid's price, updating its timestamp, possibly reordering its order book.
        If fee is not None, set the fee directly, otherwise recompute it.
        """
        self.book.update_bid(self, price, self.quantity, fee)

    def update_quantity(self, quantity: Dec,
                        fee: Optional[Dec] = None) -> None:
        """
        Update the quantity of this bid, updating its timestamp, cancelling if not positive.
        If fee is not None, set the fee directly, otherwise recompute it.
        """
        self.book.update_bid(self, self.price, quantity, fee)

    def __str__(self) -> str:
        return "Bid: " + super().__str__()


class Ask(LimitOrder):
    """An ask order. Instantiating one of these will automatically add it to its order book."""
    def __init__(self, price: Dec, quantity: Dec, fee: Dec,
                 issuer: "ag.MarketPlayer", book: "OrderBook") -> None:
        super().__init__(price, book.time, quantity, fee, issuer, book)
        # Note that the ask will not be active if quantity is not positive.
        self.book._add_new_ask_(self)

    @classmethod
    def comparator(cls, ask: "Ask"):
        """Asks are sorted first by ascending price and then by ascending time."""
        return ask.price, ask.time

    def cancel(self) -> None:
        """Remove this ask from the issuer and the order book if it's active."""
        self.book.cancel_ask(self)

    def update_price(self, price: Dec,
                     fee: Optional[Dec] = None) -> None:
        """
        Update this ask's price, updating its timestamp, possibly reordering its order book.
        If fee is not None, set the fee directly, otherwise recompute it.
        """
        self.book.update_ask(self, price, self.quantity, fee)

    def update_quantity(self, quantity: Dec,
                        fee: Optional[Dec] = None) -> None:
        """
        Update the quantity of this bid, updating its timestamp, cancelling if not positive.
        If fee is not None, set the fee directly, otherwise recompute it.
        """
        self.book.update_ask(self, self.price, quantity, fee)

    def __str__(self) -> str:
        return "Ask: " + super().__str__()


class TradeRecord:
    """A record of a single trade."""
    def __init__(self, buyer: "ag.MarketPlayer", seller: "ag.MarketPlayer",
                 price: Dec, quantity: Dec, bid_fee: Dec, ask_fee: Dec) -> None:
        self.buyer = buyer
        self.seller = seller
        self.price = price
        self.quantity = quantity
        self.bid_fee = bid_fee
        self.ask_fee = ask_fee

    def __str__(self) -> str:
        return f"{self.buyer} -> {self.seller} : {self.quantity}@{self.price}" \
               f" + ({self.bid_fee}, {self.ask_fee})"


# A type for matching functions in the order book.
Matcher = Callable[[Bid, Ask], Optional[TradeRecord]]


class OrderBook:
    """
    An order book for Havven agents to interact with.
    This one is generic, but there will have to be a market for each currency pair.
    """

    def __init__(self, model_manager: "HavvenManager", base: str, quote: str,
                 matcher: Matcher, bid_fee_fn: Callable[[Dec], Dec],
                 ask_fee_fn: Callable[[Dec], Dec],
                 match_on_order: bool = True) -> None:
        # hold onto the model to be able to access variables
        self.model_manager = model_manager

        # Define the currency pair held by this book.
        self.base: str = base
        self.quote: str = quote

        # Buys and sells should be ordered, by price first, then date.
        # Bids are ordered highest-first
        self.bids: SortedListWithKey = SortedListWithKey(key=Bid.comparator)
        # Asks are ordered lowest-first
        self.asks: SortedListWithKey = SortedListWithKey(key=Ask.comparator)

        self.bid_quants: SortedDict = SortedDict(lambda x: -x)
        self.ask_quants: SortedDict = SortedDict(lambda x: x)

        self.price: Dec = Dec('1.0')

        self.time: int = 0

        # match should be a function: match(bid, ask)
        # which resolves the given order pair,
        # which transfers buy_val of the buyer's good to the seller,
        # which transfers sell_val of the seller's good to the buyer,
        # and which returns True iff the transfer succeeded.
        self.matcher: Matcher = matcher

        # Fees will be calculated with the following functions.
        self._bid_fee_fn_: Callable[[Dec], Dec] = bid_fee_fn
        self._ask_fee_fn_: Callable[[Dec], Dec] = ask_fee_fn

        # A list of all successful trades.
        self.history: List[TradeRecord] = []

        # Try to match orders after each trade is submitted
        self.match_on_order: bool = match_on_order

    @property
    def name(self) -> str:
        """
        Return this market's name.
        """
        return f"{self.base}/{self.quote}"

    def step(self) -> None:
        """
        Advance the time on this order book by one step.
        """
        self.time += 1

    def _bid_bucket_add_(self, price: Dec, quantity: Dec) -> None:
        """
        Add a quantity to the bid bucket for a price,
        adding a new bucket if none exists.
        """
        if price in self.bid_quants:
            self.bid_quants[price] += quantity
        else:
            self.bid_quants[price] = quantity

    def _bid_bucket_deduct_(self, price: Dec, quantity: Dec) -> None:
        """
        Deduct a quantity from the bid bucket for a price,
        removing the bucket if it is emptied.
        """
        if self.bid_quants[price] == quantity:
            self.bid_quants.pop(price)
        else:
            self.bid_quants[price] -= quantity

    def _ask_bucket_add_(self, price: Dec, quantity: Dec) -> None:
        """
        Add a quantity to the ask bucket for a price,
        adding a new bucket if none exists.
        """
        if price in self.ask_quants:
            self.ask_quants[price] += quantity
        else:
            self.ask_quants[price] = quantity

    def _ask_bucket_deduct_(self, price: Dec, quantity: Dec) -> None:
        """
        Deduct a quantity from the ask bucket for a price,
        removing the bucket if it is emptied.
        """
        if self.ask_quants[price] == quantity:
            self.ask_quants.pop(price)
        else:
            self.ask_quants[price] -= quantity

    def _bid_fee_(self, price: Dec, quantity: Dec) -> Dec:
        """
        Return the fee paid on the quoted end for a bid
        of the given quantity and price.
        """
        return self._bid_fee_fn_(HavvenManager.round_decimal(price * quantity))

    def _ask_fee_(self, price: Dec, quantity: Dec) -> Dec:
        """
        Return the fee paid on the base end for an ask
        of the given quantity and price.
        """
        return self._ask_fee_fn_(quantity)

    def bid(self, price: Dec, quantity: Dec, agent: "ag.MarketPlayer") -> Optional[Bid]:
        """
        Submit a new sell order to the book.
        """
        fee = self._bid_fee_(price, quantity)

        # Fail if the value of the order exceeds the agent's available supply
        if agent.__getattribute__(f"available_{self.quote}") < HavvenManager.round_decimal(price*quantity) + fee:
            return None

        bid = Bid(HavvenManager.round_decimal(price), HavvenManager.round_decimal(quantity), HavvenManager.round_decimal(fee), agent, self)

        # Attempt to trde the bid immediately if desired.
        if self.match_on_order:
            self.match()

        return bid

    def ask(self, price: Dec, quantity: Dec, agent: "ag.MarketPlayer") -> Optional[Ask]:
        """
        Submit a new buy order to the book.
        """
        fee = self._ask_fee_(price, quantity)

        # Fail if the value of the order exceeds the agent's available supply
        if agent.__getattribute__(f"available_{self.base}") < quantity + fee:
            return None

        ask = Ask(HavvenManager.round_decimal(price), HavvenManager.round_decimal(quantity), HavvenManager.round_decimal(fee), agent, self)

        # Attempt to trde the ask immediately if desired.
        if self.match_on_order:
            self.match()

        return ask

    def buy(self, quantity: Dec, agent: "ag.MarketPlayer", premium: Dec = Dec('0.0')) -> Bid:
        """
        Buy a quantity of the sale token at the best available price.
        Optionally buy at a premium a certain fraction above the market price.
        """
        price = HavvenManager.round_decimal(self.price_to_buy_quantity(quantity) * (Dec(1) + premium))
        return self.bid(price, quantity, agent)

    def sell(self, quantity: Dec, agent: "ag.MarketPlayer", discount: Dec = Dec('0.0')) -> Ask:
        """
        Sell a quantity of the sale token at the best available price.
        Optionally sell at a discount a certain fraction below the market price.
        """
        price = HavvenManager.round_decimal(self.price_to_sell_quantity(quantity) * (Dec(1) - discount))
        return self.ask(price, quantity, agent)

    def price_to_buy_quantity(self, quantity: Dec) -> Dec:
        """
        The bid price to buy a certain quantity, ignoring fees.
        Note that this is an instantaneous metric which may be
        invalidated if intervening trades are made.
        """
        # TODO: handle the null case properly, not just use self.price
        cumulative = Dec(0)
        price = self.price
        for _price in self.ask_quants:
            price = _price
            cumulative += self.ask_quants[price]
            if cumulative >= quantity:
                break
        return price

    def price_to_sell_quantity(self, quantity: Dec) -> Dec:
        """
        The ask price to sell a certain quantity, ignoring fees.
        Note that this is an instantaneous metric which may be
        invalidated if intervening trades are made.
        """
        # TODO: handle the null case properly, not just use self.price
        cumulative = Dec(0)
        price = self.price
        for _price in self.bid_quants:
            price = _price
            cumulative += self.bid_quants[price]
            if cumulative >= quantity:
                break
        return price

    def bids_higher_or_equal(self, price: Dec) -> Iterable[Bid]:
        """
        Return an iterator of bids whose prices are no lower than the given price.
        """
        return takewhile(lambda bid: bid.price >= price, self.bids)

    def highest_bid_price(self) -> Dec:
        """
        Return the highest available buy price.
        """
        return self.bids[0].price if (len(self.bids) > 0) else self.price

    def highest_bids(self) -> Iterable[Bid]:
        """
        Return the list of highest-priced bids. May be empty if there are none.
        """
        return self.bids_higher_or_equal(self.highest_bid_price())

    def asks_lower_or_equal(self, price: Dec) -> Iterable[Bid]:
        """
        Return an iterator of asks whose prices are no higher than the given price.
        """
        return takewhile(lambda ask: ask.price <= price, self.asks)

    def lowest_ask_price(self) -> Dec:
        """
        Return the lowest available sell price.
        """
        return self.asks[0].price if (len(self.asks) > 0) else self.price

    def lowest_asks(self) -> Iterable[Bid]:
        """
        Return the list of lowest-priced asks. May be empty if there are none.
        """
        return self.asks_lower_or_equal(self.lowest_ask_price())

    def spread(self) -> Dec:
        """
        Return the gap between best buy and sell prices.
        """
        return self.lowest_ask_price() - self.highest_bid_price()

    def _add_new_bid_(self, bid: Bid) -> None:
        """
        Add a new Bid. This should be called only in the Bid constructor.
        Price, quantity, and issuer are assumed already to have been set
        in the LimitOrder super constructor.
        """

        # Do not add the Bid if it is inactive.
        # (e.g. if it was instantiated with 0 capacity)
        if not bid.active:
            return

        # Update the issuer's used quote value.
        bid.issuer.__dict__[f"used_{self.quote}"] += bid.quantity + bid.fee

        # Add to the issuer and book's records
        bid.issuer.orders.add(bid)
        self.bids.add(bid)

        # Update the cumulative price totals with the new quantity.
        self._bid_bucket_add_(bid.price, bid.quantity)

        # Advance time
        self.step()

    def update_bid(self, bid: Bid,
                   new_price: Dec,
                   new_quantity: Dec,
                   fee: Optional[Dec] = None) -> None:
        """
        Update a Bid's details in the book, recomputing fees, cached quantities,
        and the user's used currency total.
        If fee is not None, then update the fee directly, rather than recomputing it.
        """
        # Do nothing if the order is inactive.
        if not bid.active:
            return

        new_price = HavvenManager.round_decimal(new_price)
        new_quantity = HavvenManager.round_decimal(new_quantity)
        if fee is not None:
            fee = HavvenManager.round_decimal(fee)

        # Do nothing if the price and quantity would remain unchanged.
        if bid.price == new_price and bid.quantity == new_quantity:
            if fee is None or fee == bid.fee:
                return

        # If the bid is updated with a non-positive quantity, it is cancelled.
        if new_quantity <= 0:
            self.cancel_bid(bid)
            return

        # Compute the new fee.
        new_fee = fee
        if fee is None:
            new_fee = self._bid_fee_(new_price, new_quantity)

        # Update the used quantities for this bid,
        # deducting the old and crediting the new.
        bid.issuer.__dict__[f"used_{self.quote}"] += (HavvenManager.round_decimal(new_quantity*new_price) + new_fee) - \
                                                     (HavvenManager.round_decimal(bid.quantity*bid.price) + bid.fee)

        if bid.price == new_price:
            # We may assume the current price is already recorded,
            # so no need to call _bid_bucket_add_ which checks before
            # inserting. Something is wrong if the key is not found.
            #self.bid_quants[new_price] += (new_quantity - bid.quantity)
            self._bid_bucket_add_(new_price, (new_quantity - bid.quantity))

            # As the price is unchanged, order book position need not be
            # updated, just set the quantity and fee.
            bid.quantity = new_quantity
            bid.fee = new_fee
        else:
            # Deduct the old quantity from its price bucket,
            # and add the new quantity into the appropriate bucket.
            self._bid_bucket_deduct_(bid.price, bid.quantity)
            self._bid_bucket_add_(new_price, new_quantity)

            # Since the price changed, update the bid's position
            # in the book.
            self.bids.remove(bid)
            bid.price = new_price
            bid.quantity = new_quantity
            bid.fee = new_fee
            # Only set the time if the price was updated.
            bid.time = self.time
            self.bids.add(bid)

        # Advance time.
        self.step()

    def cancel_bid(self, bid: Bid) -> None:
        """
        Remove a bid from the bid list, and update cached quantity.
        """
        # We should avoid trying to cancel a bid which is already inactive.
        if not bid.active:
            return

        # Free up tokens occupied by this bid.
        bid.issuer.__dict__[f"used_{self.quote}"] -= bid.quantity + bid.fee

        # Remove this order's remaining quantity from its price bucket
        self._bid_bucket_deduct_(bid.price, bid.quantity)

        # Delete the order from the ask list and issuer.
        bid.active = False
        bid.quantity = 0
        self.bids.discard(bid)
        if len(self.bids) and self.bids[0] == bid:
            self.bids.pop(0)
        bid.issuer.orders.remove(bid)

        self.step()
        bid.issuer.notify_cancelled(bid)

    def _add_new_ask_(self, ask: Ask) -> None:
        """
        Add a new Ask. This should be called only in the Ask constructor.
        Price, quantity, and issuer are assumed already to have been set
        in the LimitOrder super constructor.
        """

        # Do not add the Ask if it is inactive.
        # (e.g. if it was instantiated with 0 capacity)
        if not ask.active:
            return

        # Update the issuer's used base value.
        ask.issuer.__dict__[f"used_{self.base}"] += ask.quantity + ask.fee

        # Add to the issuer and book's records.
        ask.issuer.orders.add(ask)
        self.asks.add(ask)

        # Update the cumulative price totals with the new quantity.
        self._ask_bucket_add_(ask.price, ask.quantity)

        # Advance time.
        self.step()

    def update_ask(self, ask: Ask,
                   new_price: Dec,
                   new_quantity: Dec,
                   fee: Optional[Dec] = None) -> None:
        """
        Update an Ask's details in the book, recomputing fees, cached quantities,
        and the user's used currency totals.
        If fee is not None, then update the fee directly, rather than recomputing it.
        """
        # Do nothing if the order is inactive.
        if not ask.active:
            return

        new_price = HavvenManager.round_decimal(new_price)
        new_quantity = HavvenManager.round_decimal(new_quantity)
        if fee is not None:
            fee = HavvenManager.round_decimal(fee)

        # Do nothing if the price and quantity would remain unchanged.
        if ask.price == new_price and ask.quantity == new_quantity:
            if fee is None or fee == ask.fee:
                return

        # If the ask is updated with a non-positive quantity, it is cancelled.
        if new_quantity <= 0:
            self.cancel_ask(ask)
            return

        # Compute the new fee
        new_fee = fee
        if fee is None:
            new_fee = self._ask_fee_(new_price, new_quantity)

        # Update the used quantities for this ask,
        # deducting the old and crediting the new.
        ask.issuer.__dict__[f"used_{self.base}"] += (new_quantity + new_fee) - \
                                                    (ask.quantity + ask.fee)

        if ask.price == new_price:
            # We may assume the current price is already recorded,
            # so no need to call _ask_bucket_add_ which checks before
            # inserting. Something is wrong if the key is not found.
            #self.ask_quants[new_price] += (new_quantity - ask.quantity)
            self._ask_bucket_add_(new_price, (new_quantity - ask.quantity))

            # As the price is unchanged, order book position need not be
            # updated, just set the quantity and fee.
            ask.quantity = new_quantity
            ask.fee = new_fee
        else:
            # Deduct the old quantity from its price bucket,
            # and add the new quantity into the appropriate bucket.
            self._ask_bucket_deduct_(ask.price, ask.quantity)
            self._ask_bucket_add_(new_price, new_quantity)

            # Since the price changed, update the ask's position
            # in the book.
            self.asks.remove(ask)
            ask.price = new_price
            ask.quantity = new_quantity
            ask.fee = new_fee
            # Only set the timestep if the price was updated.
            ask.time = self.time
            self.asks.add(ask)

        # Advance time.
        self.step()

    def cancel_ask(self, ask):
        """
        Remove an ask from the ask list, and update cached quantity.
        """
        # We should avoid trying to cancel an ask which is already inactive.
        if not ask.active:
            return

        # Free up tokens occupied by this bid.
        ask.issuer.__dict__[f"used_{self.base}"] -= ask.quantity + ask.fee

        # Remove this order's remaining quantity from its price bucket.
        self._ask_bucket_deduct_(ask.price, ask.quantity)

        # Delete order from the ask list and issuer.
        ask.active = False
        ask.quantity = 0
        self.asks.discard(ask)
        if len(self.asks) and self.asks[0] == ask:
            self.asks.pop(0)
        ask.issuer.orders.remove(ask)
        self.step()
        ask.issuer.notify_cancelled(ask)

    def match(self) -> None:
        """Match bids with asks and perform any trades that can be made."""
        prev_bid, prev_ask = None, None
        spread = Dec(0)
        # Repeatedly match the best pair of orders until no more matches can succeed.
        # Finish if there there are no orders left, or if the last match failed to remove any orders
        # This relies upon the bid and ask books being maintained ordered.
        while spread <= 0 and len(self.bids) and len(self.asks):
            if prev_bid == self.bids[0] and prev_ask == self.asks[0]:
                raise Exception("Orders didn't fill even though spread <= 0")
            if self.bids[0].quantity <= 0:
                self.bids.pop(0)
                continue
            if self.asks[0].quantity <= 0:
                self.asks.pop(0)
                continue
            # Attempt to match the highest bid with the lowest ask.
            prev_bid, prev_ask = self.bids[0], self.asks[0]
            trade = self.matcher(prev_bid, prev_ask)

            # If a trade was made, then save it in the history.
            if trade is not None:
                self.history.append(trade)

            spread = self.spread()

        self.price = HavvenManager.round_decimal((self.lowest_ask_price() + self.highest_bid_price()) / Dec(2))
