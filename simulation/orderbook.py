"""orderbook: an order book for trading in a market."""

from typing import Iterable, Callable, List, Optional, TYPE_CHECKING
from itertools import takewhile
from decimal import Decimal

# We need a fast ordered data structure to support efficient insertion and deletion of orders.
from sortedcontainers import SortedListWithKey

import agents as ag

from managers import HavvenManager


class LimitOrder:
    """A single limit order, including price, quantity, the issuer, and orderbook it belongs to."""
    def __init__(self, price: "Decimal", time: int, quantity: "Decimal", fee: "Decimal",
                 issuer: "ag.MarketPlayer", book: "OrderBook") -> None:
        self.price = price
        self.fee = fee
        self.time = time
        self.quantity = quantity
        self.issuer = issuer
        self.book = book
        self.active = True

    def cancel(self) -> None:
        """Remove this order from the issuer and the order book if it's active."""
        pass

    def update_price(self, price: "Decimal", fee: "Decimal") -> None:
        """Update this order's price, updating its timestamp, possibly reordering its order book."""
        pass

    def update_quantity(self, quantity: "Decimal", fee: "Decimal") -> None:
        """Update the quantity of this order, cancelling it if the quantity is not positive."""
        if quantity > 0:
            self.quantity = quantity
            self.fee = fee
        else:
            self.quantity = 0
            self.fee = 0
            self.cancel()

    def __str__(self) -> str:
        return f"{self.quantity}x{self.price} ({self.book.name if self.book else None}) " \
               f"@ {self.time} by {self.issuer}"


class Bid(LimitOrder):
    """A bid order. Instantiating one of these will automatically add it to its order book."""
    def __init__(self, price: "Decimal", quantity: "Decimal", fee: "Decimal",
                 issuer: "ag.MarketPlayer", book: "OrderBook") -> None:
        super().__init__(price, book.time, quantity, fee, issuer, book)
        if quantity <= 0:
            self.active = False  # bid will not be added to the orderbook
        else:
            issuer.orders.add(self)
            book.bids.add(self)
            book.step()

    @classmethod
    def comparator(cls, bid: "Bid"):
        """Bids are sorted first by descending price and then by ascending time."""
        return -bid.price, bid.time

    def cancel(self) -> None:
        if self.active:
            self.active = False
            self.book.bids.remove(self)
            self.book.step()
            self.issuer.orders.remove(self)
            self.issuer.notify_cancelled(self)

    def update_price(self, price: "Decimal", fee: "Decimal",) -> None:
        if self.active:
            self.book.bids.remove(self)
            self.price = price
            self.fee = fee
            self.time = self.book.time
            self.book.bids.add(self)
            self.book.step()

    def __str__(self) -> str:
        return "Bid: " + super().__str__()


class Ask(LimitOrder):
    """An ask order. Instantiating one of these will automatically add it to its order book."""
    def __init__(self, price: "Decimal", quantity: "Decimal", fee: "Decimal",
                 issuer: "ag.MarketPlayer", book: "OrderBook") -> None:
        super().__init__(price, book.time, quantity, fee, issuer, book)
        if quantity <= 0:
            self.active = False  # ask will not be added to the orderbook
        else:
            issuer.orders.add(self)
            book.asks.add(self)
            book.step()

    @classmethod
    def comparator(cls, ask: "Ask"):
        """Asks are sorted first by ascending price and then by ascending time."""
        return ask.price, ask.time

    def cancel(self) -> None:
        if self.active:
            self.active = False
            self.book.asks.remove(self)
            self.book.step()
            self.issuer.orders.remove(self)
            self.issuer.notify_cancelled(self)

    def update_price(self, price: "Decimal", fee: "Decimal") -> None:
        if self.active:
            self.book.asks.remove(self)
            self.price = price
            self.fee = fee
            self.time = self.book.time
            self.book.asks.add(self)
            self.book.step()

    def __str__(self) -> str:
        return "Ask: " + super().__str__()


class TradeRecord:
    """A record of a single trade."""
    def __init__(self, buyer: "ag.MarketPlayer", seller: "ag.MarketPlayer",
                 price: "Decimal", quantity: "Decimal") -> None:
        self.buyer = buyer
        self.seller = seller
        self.price = price
        self.quantity = quantity

    def __str__(self) -> str:
        return f"{self.buyer} -> {self.seller} : {self.quantity}@{self.price}"


# A type for matching functions in the order book.
Matcher = Callable[[Bid, Ask], Optional[TradeRecord]]


class OrderBook:
    """
    An order book for Havven agents to interact with.
    This one is generic, but there will have to be a market for each currency pair.
    """

    def __init__(self, model_manager: "HavvenManager", base: str, quote: str,
                 matcher: Matcher, bid_fee_fn: Callable[["Decimal"], "Decimal"],
                 ask_fee_fn: Callable[["Decimal"], "Decimal"],
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

        self.price: "Decimal" = Decimal('1.0')
        self.time: int = 0

        # match should be a function: match(bid, ask)
        # which resolves the given order pair,
        # which transfers buy_val of the buyer's good to the seller,
        # which transfers sell_val of the seller's good to the buyer,
        # and which returns True iff the transfer succeeded.
        self.matcher: Matcher = matcher

        # Fees will be calculated with the following functions.
        self.bid_fee_fn: Callable[["Decimal"], "Decimal"] = bid_fee_fn
        self.ask_fee_fn: Callable[["Decimal"], "Decimal"] = ask_fee_fn

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

    def bid(self, price: "Decimal", quantity: "Decimal", agent: "ag.MarketPlayer") -> Bid:
        """
        Submit a new sell order to the book.
        """
        fee = self.bid_fee_fn(price * quantity)
        bid = Bid(price, quantity, fee, agent, self)
        if self.match_on_order:
            self.match()
        return bid

    def ask(self, price: "Decimal", quantity: "Decimal", agent: "ag.MarketPlayer") -> Ask:
        """
        Submit a new buy order to the book.
        """
        fee = self.ask_fee_fn(quantity)
        ask = Ask(price, quantity, fee, agent, self)
        if self.match_on_order:
            self.match()
        return ask

    def buy(self, quantity: "Decimal", agent: "ag.MarketPlayer", premium: "Decimal" = 0.0) -> Bid:
        """
        Buy a quantity of the sale token at the best available price.
        Optionally buy at a premium a certain fraction above the market price.
        """
        price = self.price_to_buy_quantity(quantity) * Decimal(1 + premium)
        return self.bid(price, quantity, agent)

    def sell(self, quantity: "Decimal", agent: "ag.MarketPlayer", discount: "Decimal" = 0.0) -> Ask:
        """
        Sell a quantity of the sale token at the best available price.
        Optionally sell at a discount a certain fraction below the market price.
        """
        price = self.price_to_sell_quantity(quantity) * Decimal(1 - discount)
        return self.ask(price, quantity, agent)

    def price_to_buy_quantity(self, quantity: "Decimal") -> "Decimal":
        """
        The bid price to buy a certain quantity. Note that this is an instantaneous
        metric which may be invalidated if intervening trades are made.
        """
        cumulative = 0
        price = self.price
        for ask in self.asks:
            cumulative += ask.quantity
            price = ask.price
            if cumulative >= quantity:
                break
        return price

    def price_to_sell_quantity(self, quantity: "Decimal") -> "Decimal":
        """
        The ask price to sell a certain quantity. Note that this is an instantaneous
        metric which may be invalidated if intervening trades are made.
        """
        cumulative = 0
        price = self.price
        for bid in self.bids:
            cumulative += bid.quantity
            price = bid.price
            if cumulative >= quantity:
                break
        return price

    def bids_higher_or_equal(self, price: "Decimal") -> Iterable[Bid]:
        """Return an iterator of bids whose prices are no lower than the given price."""
        return takewhile(lambda bid: bid.price >= price, self.bids)

    def highest_bid_price(self) -> "Decimal":
        """Return the highest available buy price."""
        return self.bids[0].price if (len(self.bids) > 0) else self.price

    def highest_bids(self) -> Iterable[Bid]:
        """Return the list of highest-priced bids. May be empty if there are none."""
        return self.bids_higher_or_equal(self.highest_bid_price())

    def asks_lower_or_equal(self, price: "Decimal") -> Iterable[Bid]:
        """Return an iterator of asks whose prices are no higher than the given price."""
        return takewhile(lambda ask: ask.price <= price, self.asks)

    def lowest_ask_price(self) -> "Decimal":
        """Return the lowest available sell price."""
        return self.asks[0].price if (len(self.asks) > 0) else self.price

    def lowest_asks(self) -> Iterable[Bid]:
        """Return the list of lowest-priced asks. May be empty if there are none."""
        return self.asks_lower_or_equal(self.lowest_ask_price())

    def spread(self) -> "Decimal":
        """Return the gap between best buy and sell prices."""
        return self.lowest_ask_price() - self.highest_bid_price()

    def round_float(self, value: float) -> "Decimal":
        return round(Decimal(value), self.model_manager.currency_precision)

    def round_decimal(self, value: "Decimal") -> "Decimal":
        return round(value, self.model_manager.currency_precision)

    def match(self) -> None:
        """Match bids with asks and perform any trades that can be made."""
        prev_bid, prev_ask = None, None
        spread = 0.0
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

            spread = self.spread()

        self.price = (self.lowest_ask_price() + self.highest_bid_price()) / 2
