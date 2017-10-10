"""orderbook: an order book for trading in a market."""

from typing import Iterable, Callable, List, Optional
from itertools import takewhile

# We need a fast ordered data structure to support efficient insertion and deletion of orders.
from sortedcontainers import SortedListWithKey

import agents as ag

class LimitOrder:
    """A single limit order, including price, quantity, the issuer, and orderbook it belongs to."""
    def __init__(self, price: float, time: int, quantity: float,
                 issuer: "ag.MarketPlayer", book: "OrderBook") -> None:
        self.price = price
        self.time = time
        self.quantity = quantity
        self.issuer = issuer
        self.book = book
        self.active = True

    def cancel(self) -> None:
        """Remove this order from the issuer and the order book if it's active."""
        pass

    def update_price(self, price: float) -> None:
        """Update this order's price, updating its timestamp, possibly reordering its order book."""
        pass

    def update_quantity(self, quantity: float) -> None:
        """Update the quantity of this order, cancelling it if the quantity is not positive."""
        if quantity > 0:
            self.quantity = quantity
        else:
            self.quantity = 0
            self.cancel()

    def __str__(self) -> str:
        return f"{self.quantity}x{self.price} ({self.book.name if self.book else None}) " \
               f"@ {self.time} by {self.issuer}"

class Bid(LimitOrder):
    """A bid order. Instantiating one of these will automatically add it to its order book."""
    def __init__(self, price: float, quantity: float,
                 issuer: "ag.MarketPlayer", book: "OrderBook") -> None:
        super().__init__(price, book.time, quantity, issuer, book)
        if quantity <= 0:
            self.cancel()
        else:
            issuer.orders.add(self)
            book.bids.add(self)
            book.step()

    @classmethod
    def comparator(cls, bid: "Bid"):
        """Bids are sorted first by descending price and then by ascending time."""
        return (-bid.price, bid.time)

    def cancel(self) -> None:
        if self.active:
            self.active = False
            self.book.bids.remove(self)
            self.book.step()
            self.issuer.orders.remove(self)
            self.issuer.notify_cancelled(self)

    def update_price(self, price: float) -> None:
        if self.active:
            self.book.bids.remove(self)
            self.price = price
            self.time = self.book.time
            self.book.bids.add(self)
            self.book.step()

    def __str__(self) -> str:
        return "Bid: " + super().__str__()


class Ask(LimitOrder):
    """An ask order. Instantiating one of these will automatically add it to its order book."""
    def __init__(self, price: float, quantity: float,
                 issuer: "ag.MarketPlayer", book: "OrderBook") -> None:
        super().__init__(price, book.time, quantity, issuer, book)
        if quantity <= 0:
            self.cancel()
        else:
            issuer.orders.add(self)
            book.asks.add(self)
            book.step()

    @classmethod
    def comparator(cls, ask: "Ask"):
        """Asks are sorted first by ascending price and then by ascending time."""
        return (ask.price, ask.time)

    def cancel(self) -> None:
        if self.active:
            self.active = False
            self.book.asks.remove(self)
            self.book.step()
            self.issuer.orders.remove(self)
            self.issuer.notify_cancelled(self)

    def update_price(self, price: float) -> None:
        if self.active:
            self.book.asks.remove(self)
            self.price = price
            self.time = self.book.time
            self.book.asks.add(self)
            self.book.step()

    def __str__(self) -> str:
        return "Ask: " + super().__str__()


class TradeRecord:
    """A record of a single trade."""
    def __init__(self, buyer: "ag.MarketPlayer", seller: "ag.MarketPlayer",
                 price: float, quantity: float) -> None:
        self.buyer = buyer
        self.seller = seller
        self.price = price
        self.quantity = quantity

    def __str__(self) -> str:
        return f"{self.buyer} -> {self.seller} : {self.quantity}@{self.price}"


# A type for matching functions in the order book.
Matcher = Callable[[Bid, Ask], Optional[TradeRecord]]

class OrderBook:
    """An order book for Havven agents to interact with.""" \
    """This one is generic, but there will have to be a market for each currency pair."""

    def __init__(self, base: str, quote: str, matcher: Matcher, match_on_order: bool = True) -> None:
        # Define the currency pair held by this book.
        self.base: str = base
        self.quote: str = quote

        # Buys and sells should be ordered, by price first, then date.
        # Bids are ordered highest-first
        self.bids: SortedListWithKey = SortedListWithKey(key=Bid.comparator)
        # Asks are ordered lowest-first
        self.asks: SortedListWithKey = SortedListWithKey(key=Ask.comparator)

        self.price: float = 1.0
        self.time: int = 0

        # match should be a function: match(bid, ask)
        # which resolves the given order pair,
        # which transfers buy_val of the buyer's good to the seller,
        # which transfers sell_val of the seller's good to the buyer,
        # and which returns True iff the transfer succeeded.
        self.matcher: Matcher = matcher

        # A list of all successful trades.
        self.history: List[TradeRecord] = []

        # Try to match orders after each trade is submitted
        self.match_on_order: bool = match_on_order

    @property
    def name(self) -> str:
        """Return this market's name."""
        return f"{self.base}/{self.quote}"

    def step(self) -> None:
        """Advance the time on this order book by one step."""
        self.time += 1

    def bid(self, price: float, quantity: float, agent: "ag.MarketPlayer") -> Bid:
        """Submit a new sell order to the book."""
        bid = Bid(price, quantity, agent, self)
        if self.match_on_order:
            self.match()
        return bid

    def ask(self, price: float, quantity: float, agent: "ag.MarketPlayer") -> Ask:
        """Submit a new buy order to the book."""
        ask = Ask(price, quantity, agent, self)
        if self.match_on_order:
            self.match()
        return ask

    def buy(self, quantity: float, agent: "ag.MarketPlayer", premium: float = 0) -> Bid:
        """Buy a quantity of the sale token at the best available price."""
        price = self.price_to_buy_quantity(quantity)
        return self.bid(price, quantity, agent)

    def sell(self, quantity: float, agent: "ag.MarketPlayer", discount: float = 0) -> Ask:
        """Sell a quantity of the sale token at the best available price."""
        price = self.price_to_sell_quantity(quantity)
        return self.ask(price, quantity, agent)

    def price_to_buy_quantity(self, quantity: float) -> float:
        """The bid price to buy a certain quantity."""
        cumulative = 0
        price = self.price
        for ask in self.asks:
            cumulative += ask.quantity
            price = ask.price
            if cumulative >= quantity:
                break
        return price

    def price_to_sell_quantity(self, quantity: float) -> float:
        """The ask price to sell a certain quantity."""
        cumulative = 0
        price = self.price
        for bid in self.bids:
            cumulative += bid.quantity
            price = bid.price
            if cumulative >= quantity:
                break
        return price

    def bids_higher_or_equal(self, price: float) -> Iterable[Bid]:
        """Return an iterator of bids whose prices are no lower than the given price."""
        return takewhile(lambda bid: bid.price >= price, self.bids)

    def highest_bid_price(self) -> float:
        """Return the highest available buy price."""
        return self.bids[0].price if (len(self.bids) > 0) else self.price

    def highest_bids(self) -> Iterable[Bid]:
        """Return the list of highest-priced bids. May be empty if there are none."""
        return self.bids_higher_or_equal(self.highest_bid_price())

    def asks_lower_or_equal(self, price: float) -> Iterable[Bid]:
        """Return an iterator of asks whose prices are no higher than the given price."""
        return takewhile(lambda ask: ask.price <= price, self.asks)

    def lowest_ask_price(self) -> float:
        """Return the lowest available sell price."""
        return self.asks[0].price if (len(self.asks) > 0) else self.price

    def lowest_asks(self) -> Iterable[Bid]:
        """Return the list of lowest-priced asks. May be empty if there are none."""
        return self.asks_lower_or_equal(self.lowest_ask_price())

    def spread(self) -> float:
        """Return the gap between best buy and sell prices."""
        return self.lowest_ask_price() - self.highest_bid_price()

    def match(self) -> None:
        """Match bids with asks and perform any trades that can be made."""
        prev_bid, prev_ask = None, None
        spread = 0.0
        # Repeatedly match the best pair of orders until no more matches can succeed.
        # Finish if there there are no orders left, or if the last match failed to remove any orders
        # This relies upon the bid and ask books being maintained ordered.
        while spread <= 0 and len(self.bids) and len(self.asks) and \
              not (prev_bid == self.bids[0] and prev_ask == self.asks[0]):

            # Attempt to match the highest bid with the lowest ask.
            prev_bid, prev_ask = self.bids[0], self.asks[0]

            trade = self.matcher(prev_bid, prev_ask)

            # If a trade was made, then save it in the history.
            if trade is not None:
                self.history.append(trade)

            spread = self.spread()

        self.price = (self.lowest_ask_price() + self.highest_bid_price()) / 2
