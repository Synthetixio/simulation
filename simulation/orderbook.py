"""orderbook: an order book for trading in a market."""

from typing import Iterable
from itertools import takewhile
# We need a fast ordered data structure in order to support efficient insertion and deletion of orders.
from sortedcontainers import SortedListWithKey
from agents import MarketPlayer

class Order:
    """A single order, including price, quantity, and the agent which submitted it."""
    def __init__(self, price:float, time:int, quantity:float, issuer:MarketPlayer, book:"OrderBook") -> None:
        self.price = price
        self.time = time
        self.quantity = quantity
        self.issuer = issuer
        self.book = book
        self.active = True
    
    def update_quantity(self, quantity:float) -> None:
        if quantity >= 0:
            self.quantity = quantity
        else:
            self.quantity = 0
            self.cancel()
    
    def __str__(self) -> str:
        return f"{self.quantity}x{self.price} @ {self.time} by {self.issuer}"

class Bid(Order):
    """A bid order. Instantiating one of these will automatically add it to its order book."""
    def __init__(self, price:float, quantity:float, issuer:MarketPlayer, book:"OrderBook") -> None:
        super().__init__(price, book.time, quantity, issuer, book)
        if quantity <= 0:
            self.active = False
        else:
            issuer.orders.add(self)
            book.buy_orders.add(self)
            book.step()

    @classmethod
    def comparator(cls, bid:"Bid"):
        return (-bid.price, bid.time)

    def cancel(self) -> None:
        if self.active:
            self.active = False
            self.book.buy_orders.remove(self)
            self.book.step()
            self.issuer.orders.remove(self)
            self.issuer.notify_cancelled(self)

    def update_price(self, price:float) -> None:
        if self.active:
            self.book.buy_orders.remove(self)
            self.price = price
            self.time = self.book.time
            self.book.buy_orders.add(self)
            self.book.step()
    
    def __str__(self) -> str:
        return "Bid: " + super().__str__()


class Ask(Order):
    """An ask order. Instantiating one of these will automatically add it to its order book."""
    def __init__(self, price:float, quantity:float, issuer:MarketPlayer, book:"OrderBook") -> None:
        super().__init__(price, book.time, quantity, issuer, book)
        if quantity <= 0:
            self.active = False
        else:
            issuer.orders.add(self)
            book.sell_orders.add(self)
            book.step()

    @classmethod
    def comparator(cls, ask:"Ask"):
        return (ask.price, ask.time)

    def cancel(self) -> None:
        if self.active:
            self.active = False
            self.book.sell_orders.remove(self)
            self.book.step()
            self.issuer.orders.remove(self)
            self.issuer.notify_cancelled(self)

    def update_price(self, price:float) -> None:
        if self.active:
            self.book.sell_orders.remove(self)
            self.price = price
            self.time = self.book.time
            self.book.sell_orders.add(self)
            self.book.step()

    def __str__(self) -> str:
        return "Ask: " + super().__str__()

class OrderBook:
    """An order book for Havven agents to interact with.
    This one is generic, but there will have to be three markets in Havven (nom-cur, fiat-cur, fiat-nom)."""

    def __init__(self, name, match_function, match_on_order=True) -> None:
        self.name = name
        # Buys and sells should be ordered, by price first, then date.
        # Bids are ordered highest-first
        self.buy_orders = SortedListWithKey(key=Bid.comparator)
        # Asks are ordered lowest-first
        self.sell_orders = SortedListWithKey(key=Ask.comparator)

        # TODO: Update the underlying price as we go along.
        self.price = 1.0
        self.time = 0

        # match should be a function: match(bid, ask)
        # which resolves the given order pair,
        # which transfers buy_val of the buyer's good to the seller,
        # which transfers sell_val of the seller's good to the buyer,
        # and which returns True if the transfer succeeded.
        self.match_function = match_function

        # Try to match orders after each trade is submitted
        self.match_on_order = match_on_order

    def step(self) -> None:
        """Advance the time on this order book by one step."""
        self.time += 1

    def bid(self, price:float, quantity:float, agent:MarketPlayer) -> Bid:
        """Submit a new sell order to the book."""
        b = Bid(price, quantity, agent, self)
        if self.match_on_order:
            self.match()
        return b

    def ask(self, price:float, quantity:float, agent:MarketPlayer) -> Ask:
        """Submit a new buy order to the book."""
        a = Ask(price, quantity, agent, self)
        if self.match_on_order:
            self.match()
        return a
    
    def buy(self, quantity:float, agent:MarketPlayer, premium=0) -> Bid:
        """Buy a quantity of the sale token at the best available price."""
        lowest_ask = self.lowest_ask_price()
        price = (self.price if lowest_ask is None else lowest_ask) + premium
        return self.bid(price, quantity, agent)
    
    def sell(self, quantity:float, agent:MarketPlayer, discount=0) -> Ask:
        """Sell a quantity of the sale token at the best available price."""
        highest_bid = self.highest_bid_price()
        price = (self.price if highest_bid is None else highest_bid) - discount
        return self.ask(price, quantity, agent)

    def bids_higher_or_equal(self, price) -> Iterable[Bid]:
        """Return an iterator of bids whose prices are no lower than the given price."""
        return takewhile(lambda bid: bid.price >= price, self.buy_orders)
    
    def highest_bid_price(self) -> float:
        """Return the highest available buy price."""
        return self.buy_orders[0].price if len(self.buy_orders) else self.price

    def highest_bids(self) -> Iterable[Bid]:
        """Return the list of highest-priced bids. May be empty if there are none."""
        return self.bids_higher_or_equal(self.highest_bid_price())

    def asks_lower_or_equal(self, price) -> Iterable[Bid]:
        """Return an iterator of asks whose prices are no higher than the given price."""
        return takewhile(lambda ask:ask.price <= price, self.sell_orders)

    def lowest_ask_price(self) -> float:
        """Return the lowest available sell price."""
        return self.sell_orders[0].price if len(self.sell_orders) else self.price

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
        while spread <= 0 and len(self.buy_orders) and len(self.sell_orders) and \
              not (prev_bid == self.buy_orders[0] and prev_ask == self.sell_orders[0]):
            prev_bid, prev_ask = self.buy_orders[0], self.sell_orders[0]
            self.match_function(prev_bid, prev_ask)
            spread = self.spread()
        
        self.price = (self.lowest_ask_price() + self.highest_bid_price()) / 2