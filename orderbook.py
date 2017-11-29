"""orderbook: an order book for trading in a market."""

from typing import Iterable, Callable, List, Optional, Tuple
from decimal import Decimal as Dec
from itertools import takewhile
from collections import namedtuple

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

        self.fee = fee
        """An extra fee charged on top of the face value of the order."""

        self.time = time
        """The time this order was created, or last modified."""

        self.quantity = quantity
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
        self.book.add_new_bid(self)

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
        self.book.add_new_ask(self)

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
    def __init__(self, buyer: "ag.MarketPlayer", seller: "ag.MarketPlayer", book: "OrderBook",
                 price: Dec, quantity: Dec, bid_fee: Dec, ask_fee: Dec, time: int) -> None:
        self.buyer = buyer
        self.seller = seller
        self.book = book
        self.price = price
        self.quantity = quantity
        self.bid_fee = bid_fee
        self.ask_fee = ask_fee
        self.completion_time = time

    def __str__(self) -> str:
        return f"{self.buyer} -> {self.seller} : {self.quantity}@{self.price}" \
               f" + ({self.bid_fee}, {self.ask_fee}) t:{self.completion_time} {self.book.name}"


# A type for matching functions in the order book.
Matcher = Callable[[Bid, Ask], Optional[TradeRecord]]


class OrderBook:
    """
    An order book for Havven agents to interact with.

    The order book will handle trades between a particular currency pair,
    consisting of the "base" and "quoted" currencies.
    This is generic; there will have to be a book for each pair.

    The book holds two lists of orders, asks and bids. Each order has a price,
    quantity, and time of issue. They are ordered in the book by price, and then
    by time.
    An ask is an order to sell the base currency, while a bid is an order to buy it.
    Therefore, merchants filing asks hold the base currency, while those filing bids
    hold the quoted currency.
    Order prices are a quantity of the quoted currency per unit of the base currency.
    Order quantities shall be a quantity of the base currency to trade.

    If a bid has a higher price than an ask, then the orders may match,
    in which case the issuers trade at the price on the earlier-issued order.
    The seller will transfer the smaller quantity of the base currency
    to the buyer, while the buyer will transfer that quantity times the match price
    of the quoted currency to the seller.

    An order may be partially filled, in which case its quantity will be decreased.
    If an order's remaining quantity falls to zero, the order is completely filled
    and struck off the book.
    A user may cancel bids they have issued at any time.

    If an ask is placed at a price lower or equal to the highest bid price, it
    will be immediately matched against the most favourable orders in turn until it is completely
    filled (if possible).
    The operation is symmetric if a bid is placed at a price higher than the lowest
    ask price.
    """

    def __init__(self, model_manager: "HavvenManager",
                 base: str, quote: str,
                 matcher: Matcher,
                 quoted_fee: Callable[[Dec], Dec],
                 base_fee: Callable[[Dec], Dec],
                 quoted_qty_rcvd: Callable[[Dec], Dec],
                 base_qty_rcvd: Callable[[Dec], Dec],
                 match_on_order: bool = True) -> None:
        # hold onto the model to be able to access variables
        self.model_manager = model_manager

        # Define the currency pair held by this book.
        self.base = base
        self.quoted = quote

        # Buys and sells should be ordered, by price first, then date.
        # Bids are ordered highest-first
        self.bids = SortedListWithKey(key=Bid.comparator)
        # Asks are ordered lowest-first
        self.asks = SortedListWithKey(key=Ask.comparator)

        # These dicts store the quantities demanded or supplied at each price.
        self.bid_price_buckets = SortedDict(lambda x: -x)
        self.ask_price_buckets = SortedDict(lambda x: x)

        self.cached_price: Dec = Dec('1.0')
        self.last_cached_price_time: int = 0

        self.time: int = 0

        # match should be a function: match(bid, ask)
        # which resolves the given order pair,
        # which transfers buy_val of the buyer's good to the seller,
        # which transfers sell_val of the seller's good to the buyer,
        # and which returns True iff the transfer succeeded.
        self.matcher = matcher

        # Fees will be calculated with the following functions.
        self.quoted_fee = quoted_fee
        self.base_fee = base_fee
        self.quoted_qty_rcvd = quoted_qty_rcvd
        self.base_qty_rcvd = base_qty_rcvd

        # A list of all successful trades.
        self.history: List[TradeRecord] = []

        # A list keeping track of each tick's high, low, open, close
        self.candle_data: List[List[Dec]] = [[Dec(1), Dec(1), Dec(1), Dec(1)]]
        self.price_data: List[Dec] = [self.cached_price]
        self.volume_data: List[Dec] = [Dec(0)]

        # Try to match orders after each trade is submitted
        self.match_on_order: bool = match_on_order

    @property
    def name(self) -> str:
        """
        Return this market's name.
        """
        return f"{self.base}/{self.quoted}"

    @property
    def price(self) -> Dec:
        """
        Return the rolling average of the price, only calculate it once per tick
        """
        if self.model_manager.time <= self.last_cached_price_time:
            return self.cached_price

        if self.model_manager.volume_weighted_average:
            return self.weighted_rolling_price_average(self.model_manager.rolling_avg_time_window)
        else:
            return self.rolling_price_average(self.model_manager.rolling_avg_time_window)

    def rolling_price_average(self, time_window: int) -> Dec:
        """
        Return the average trading price over the last time_window periods.
        """
        total = Dec(0)
        counted = 0

        for item in reversed(self.history):
            if item.completion_time < self.model_manager.time - time_window:
                break
            total += item.price
            counted += 1

        if counted == 0:
            self.cached_price = self.cached_price
        else:
            self.cached_price = total / Dec(counted)

        self.last_cached_price_time = self.model_manager.time
        return self.cached_price

    def weighted_rolling_price_average(self, time_window: int) -> Dec:
        """
        Return the average trading price over the last time_window periods, weighted by quantity per trade.
        """
        total = Dec(0)
        counted_vol = Dec(0)

        for item in reversed(self.history):
            if item.completion_time < self.model_manager.time - time_window:
                break
            total += item.price * item.quantity
            counted_vol += item.quantity

        if counted_vol == Dec(0):
            self.cached_price = self.cached_price
        else:
            self.cached_price = total / counted_vol

        self.last_cached_price_time = self.model_manager.time
        return self.cached_price

    def step(self) -> None:
        """
        Advance the time on this order book by one step.
        """
        self.time += 1

    def step_history(self) -> None:
        """Add new data points to update"""

        if len(self.candle_data) > 1 and self.candle_data[-1][3] is None:
            self.candle_data[-1][1] = self.candle_data[-1][0]
            self.candle_data[-1][2] = self.candle_data[-1][0]
            self.candle_data[-1][3] = self.candle_data[-1][0]
        self.candle_data.append([self.candle_data[-1][1], None, None, None])

        self.volume_data.append(Dec(0))
        for item in reversed(self.history):
            if item.completion_time != self.model_manager.time:
                break
            self.volume_data[-1] += item.quantity

        self.price_data.append(self.cached_price)

    def _bid_bucket_add(self, price: Dec, quantity: Dec) -> None:
        """
        Add a quantity to the bid bucket for a price,
        adding a new bucket if none exists.
        """
        if price in self.bid_price_buckets:
            self.bid_price_buckets[price] += quantity
        else:
            self.bid_price_buckets[price] = quantity

    def _bid_bucket_deduct(self, price: Dec, quantity: Dec) -> None:
        """
        Deduct a quantity from the bid bucket for a price,
        removing the bucket if it is emptied.
        """
        if self.bid_price_buckets[price] == quantity:
            self.bid_price_buckets.pop(price)
        else:
            self.bid_price_buckets[price] -= quantity

    def _ask_bucket_add(self, price: Dec, quantity: Dec) -> None:
        """
        Add a quantity to the ask bucket for a price,
        adding a new bucket if none exists.
        """
        if price in self.ask_price_buckets:
            self.ask_price_buckets[price] += quantity
        else:
            self.ask_price_buckets[price] = quantity

    def _ask_bucket_deduct(self, price: Dec, quantity: Dec) -> None:
        """
        Deduct a quantity from the ask bucket for a price,
        removing the bucket if it is emptied.
        """
        if self.ask_price_buckets[price] == quantity:
            self.ask_price_buckets.pop(price)
        else:
            self.ask_price_buckets[price] -= quantity

    def buyer_fee(self, price: Dec, quantity: Dec) -> Dec:
        """
        Return the fee paid on the quoted end (by the buyer) for a bid
        of the given quantity and price.
        """
        return self.quoted_fee(HavvenManager.round_decimal(price * quantity))

    def seller_fee(self, price: Dec, quantity: Dec) -> Dec:
        """
        Return the fee paid on the base end (by the seller) for an ask
        of the given quantity and price.
        """
        return self.base_fee(quantity)

    def seller_received_quantity(self, price: Dec, quantity: Dec) -> Dec:
        """
        The quantity of the quoted currency received by a seller (fees deducted).
        """
        return self._quoted_qty_received_fn_(HavvenManager.round_decimal(price * quantity))

    def buyer_received_quantity(self, price: Dec, quantity: Dec) -> Dec:
        """
        The quantity of the base currency received by a buyer (fees deducted).
        """
        return self.base_qty_rcvd(quantity)

    def bid(self, price: Dec, quantity: Dec, agent: "ag.MarketPlayer") -> Optional[Bid]:
        """
        Submit a new sell order to the book.
        """
        quantity = HavvenManager.round_decimal(quantity)

        # Disallow empty orders.
        if quantity == Dec(0):
            return None

        # Compute the fee to be paid.
        fee = self.buyer_fee(price, quantity)

        # Fail if the value of the order exceeds the agent's available supply.
        agent.round_values()
        if agent.__getattribute__(f"available_{self.quoted}") < HavvenManager.round_decimal(price*quantity) + fee:
            return None

        bid = Bid(price, quantity, fee, agent, self)

        # Attempt to trade the bid immediately.
        if self.match_on_order:
            self.match()

        return bid

    def ask(self, price: Dec, quantity: Dec, agent: "ag.MarketPlayer") -> Optional[Ask]:
        """
        Submit a new buy order to the book.
        """
        quantity = HavvenManager.round_decimal(quantity)

        # Disallow empty orders.
        if quantity == Dec(0):
            return None

        # Compute the fee to be paid.
        fee = self.seller_fee(price, quantity)

        # Fail if the value of the order exceeds the agent's available supply.
        agent.round_values()
        if agent.__getattribute__(f"available_{self.base}") < quantity + fee:
            return None

        ask = Ask(price, quantity, fee, agent, self)

        # Attempt to trade the ask immediately.
        if self.match_on_order:
            self.match()

        return ask

    def buy(self, quantity: Dec, agent: "ag.MarketPlayer") -> Optional[Bid]:
        """
        Buy a quantity of the base currency at the best available price.
        """
        price = HavvenManager.round_decimal(self.price_to_buy_quantity(quantity))
        return self.bid(price, quantity, agent)

    def sell(self, quantity: Dec, agent: "ag.MarketPlayer") -> Optional[Ask]:
        """
        Sell a quantity of the base currency at the best available price.
        """
        price = HavvenManager.round_decimal(self.price_to_sell_quantity(quantity))
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
        for _price in self.ask_price_buckets:
            price = _price
            cumulative += self.ask_price_buckets[price]
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
        for _price in self.bid_price_buckets:
            price = _price
            cumulative += self.bid_price_buckets[price]
            if cumulative >= quantity:
                break
        return price

    def asks_not_higher_base_quantity(self, price: Dec, quoted_capital: Optional[Dec] = None) -> Dec:
        """
        Return the quantity of base currency you would obtain offering no more
        than a certain price, if you could spend up to a quantity of the quoted currency.
        """
        bought = Dec(0)
        sold = Dec(0)
        for ask in self.asks_not_higher(price):
            next_sold = HavvenManager.round_decimal(ask.price * ask.quantity)
            if quoted_capital is not None and sold + next_sold > quoted_capital:
                bought += HavvenManager.round_decimal(ask.quantity * (quoted_capital - sold) / next_sold)
                break
            sold += next_sold
            bought += ask.quantity
        return bought

    def bids_not_lower_quoted_quantity(self, price: Dec, base_capital: Optional[Dec] = None) -> Dec:
        """
        Return the quantity of quoted currency you would obtain offering no less
        than a certain price, if you could spend up to a quantity of the base currency.
        """
        bought = Dec(0)
        sold = Dec(0)
        for bid in self.bids_not_lower(price):
            if base_capital is not None and sold + bid.quantity > base_capital:
                bought += HavvenManager.round_decimal((base_capital - sold) * bid.price)
                break
            sold += bid.quantity
            bought += HavvenManager.round_decimal(bid.price * bid.quantity)
        return bought

    def bids_not_lower(self, price: Dec) -> Iterable[Bid]:
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
        return self.bids_not_lower(self.highest_bid_price())

    def highest_bid_quantity(self) -> Dec:
        """
        Return the quantity of the base currency demanded at the highest bid price.
        """
        # Enclose in Decimal constructor in case sum is 0.
        return Dec(sum(b.quantity for b in self.highest_bids()))

    def asks_not_higher(self, price: Dec) -> Iterable[Bid]:
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
        return self.asks_not_higher(self.lowest_ask_price())

    def lowest_ask_quantity(self) -> Dec:
        """
        Return the quantity of the base currency supplied at the lowest ask price.
        """
        # Enclose in Decimal constructor in case sum is 0.
        return Dec(sum(a.quantity for a in self.lowest_asks()))

    def spread(self) -> Dec:
        """
        Return the gap between best buy and sell prices.
        """
        return self.lowest_ask_price() - self.highest_bid_price()

    def add_new_bid(self, bid: Bid) -> None:
        """
        Add a new Bid. This should be called only in the Bid constructor.
        Price, quantity, and issuer are assumed already to have been set
        in the LimitOrder super constructor.
        """

        # Do not add the Bid if it is inactive.
        # (e.g. if it was instantiated with 0 capacity)
        if not bid.active:
            return

        # Update the issuer's unavailable quote value.
        bid.issuer.__dict__[f"unavailable_{self.quoted}"] += bid.quantity * bid.price + bid.fee

        # Add to the issuer and book's records
        bid.issuer.orders.append(bid)
        self.bids.add(bid)

        # Update the cumulative price totals with the new quantity.
        self._bid_bucket_add(bid.price, bid.quantity)

        # Advance time
        self.step()

    def update_bid(self, bid: Bid,
                   new_price: Dec,
                   new_quantity: Dec,
                   fee: Optional[Dec] = None) -> None:
        """
        Update a Bid's details in the book, recomputing fees, cached quantities,
        and the user's unavailable currency total.
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
            if fee == bid.fee or fee is None:
                return
            else:
                print(bid)
                raise Exception("Fee changed, but price and quantity are unchanged...")

        # If the bid is updated with a non-positive quantity, it is cancelled.
        if new_quantity <= 0:
            self.cancel_bid(bid)
            return

        # Compute the new fee.
        new_fee = fee
        if fee is None:
            new_fee = self.buyer_fee(new_price, new_quantity)

        # Update the unavailable quantities for this bid,
        # deducting the old and crediting the new.
        bid.issuer.__dict__[f"unavailable_{self.quoted}"] += \
            (HavvenManager.round_decimal(new_quantity*new_price) + new_fee) - \
            (HavvenManager.round_decimal(bid.quantity*bid.price) + bid.fee)

        if bid.price == new_price:
            # We may assume the current price is already recorded,
            # so no need to call _bid_bucket_add_ which checks before
            # inserting. Something is wrong if the key is not found.
            self.bid_price_buckets[new_price] += (new_quantity - bid.quantity)

            # As the price is unchanged, order book position need not be
            # updated, just set the quantity and fee.
            bid.quantity = new_quantity
            bid.fee = new_fee
        else:
            # Deduct the old quantity from its price bucket,
            # and add the new quantity into the appropriate bucket.
            self._bid_bucket_deduct(bid.price, bid.quantity)
            self._bid_bucket_add(new_price, new_quantity)

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
        bid.issuer.__dict__[f"unavailable_{self.quoted}"] -= bid.quantity * bid.price + bid.fee

        # Remove this order's remaining quantity from its price bucket
        self._bid_bucket_deduct(bid.price, bid.quantity)

        # Delete the order from the ask list and issuer.
        self.bids.remove(bid)
        bid.issuer.orders.remove(bid)
        bid.active = False
        self.step()
        bid.issuer.notify_cancelled(bid)

    def add_new_ask(self, ask: Ask) -> None:
        """
        Add a new Ask. This should be called only in the Ask constructor.
        Price, quantity, and issuer are assumed already to have been set
        in the LimitOrder super constructor.
        """

        # Do not add the Ask if it is inactive.
        # (e.g. if it was instantiated with 0 capacity)
        if not ask.active:
            return

        # Update the issuer's unavailable base value.
        ask.issuer.__dict__[f"unavailable_{self.base}"] += ask.quantity + ask.fee

        # Add to the issuer and book's records.
        ask.issuer.orders.append(ask)
        self.asks.add(ask)

        # Update the cumulative price totals with the new quantity.
        self._ask_bucket_add(ask.price, ask.quantity)

        # Advance time.
        self.step()

    def update_ask(self, ask: Ask,
                   new_price: Dec,
                   new_quantity: Dec,
                   fee: Optional[Dec] = None) -> None:
        """
        Update an Ask's details in the book, recomputing fees, cached quantities,
        and the user's unavailable currency totals.
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
            else:
                print(ask)
                raise Exception("Fee changed, but price and quantity are unchanged...")

        # If the ask is updated with a non-positive quantity, it is cancelled.
        if new_quantity <= 0:
            self.cancel_ask(ask)
            return

        # Compute the new fee
        new_fee = fee
        if fee is None:
            new_fee = self.seller_fee(new_price, new_quantity)

        # Update the unavailable quantities for this ask,
        # deducting the old and crediting the new.
        ask.issuer.__dict__[f"unavailable_{self.base}"] += \
            (new_quantity + new_fee) - (ask.quantity + ask.fee)

        if ask.price == new_price:
            # We may assume the current price is already recorded,
            # so no need to call _ask_bucket_add_ which checks before
            # inserting. Something is wrong if the key is not found.
            self.ask_price_buckets[new_price] += (new_quantity - ask.quantity)

            # As the price is unchanged, order book position need not be
            # updated, just set the quantity and fee.
            ask.quantity = new_quantity
            ask.fee = new_fee
        else:
            # Deduct the old quantity from its price bucket,
            # and add the new quantity into the appropriate bucket.
            self._ask_bucket_deduct(ask.price, ask.quantity)
            self._ask_bucket_add(new_price, new_quantity)

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
        ask.issuer.__dict__[f"unavailable_{self.base}"] -= ask.quantity + ask.fee

        # Remove this order's remaining quantity from its price bucket.
        self._ask_bucket_deduct(ask.price, ask.quantity)

        # Delete order from the ask list and issuer.
        self.asks.remove(ask)
        ask.issuer.orders.remove(ask)
        ask.active = False
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

            # Attempt to match the highest bid with the lowest ask.
            prev_bid, prev_ask = self.bids[0], self.asks[0]
            trade = self.matcher(prev_bid, prev_ask)

            # If a trade was made, then save it in the history.
            if trade is not None:
                self.history.append(trade)
                trade.buyer.notify_trade(trade)
                trade.seller.notify_trade(trade)

                # if no closing data yet, initialise
                if not self.candle_data[-1][1]:
                    self.candle_data[-1][2] = trade.price
                    self.candle_data[-1][3] = trade.price

                self.candle_data[-1][1] = trade.price

                if trade.price > self.candle_data[-1][2]:
                    self.candle_data[-1][2] = trade.price

                if trade.price < self.candle_data[-1][3]:
                    self.candle_data[-1][3] = trade.price

            spread = self.spread()

    def do_single_match(self) -> TradeRecord:
        """Match the top bid with the lowest ask for testing step by step"""
        if len(self.bids) and len(self.asks):
            prev_bid, prev_ask = self.bids[0], self.asks[0]
            trade = self.matcher(prev_bid, prev_ask)

            # If a trade was made, then save it in the history.
            if trade is not None:
                self.history.append(trade)
                trade.buyer.notify_trade(trade)
                trade.seller.notify_trade(trade)

            return trade

        raise Exception("Either no bids or no asks in orderbook, when attempting to do single match")
