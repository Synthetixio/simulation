"""orderbook: an order book for trading in a market."""

# TODO: Convert this all to use python's Decimal representation


# We need a fast ordered data structure in order to support efficient insertion and deletion of orders.
from sortedcontainers import SortedListWithKey

class Order:
    """A single order, including price, quantity, and the agent which submitted it."""
    def __init__(self, price, time, quantity, issuer, book):
        self.price = price
        self.time = time
        self.quantity = quantity
        self.issuer = issuer
        self.book = book
        self.active = True

class Bid(Order):
    @classmethod
    def comparator(cls, bid):
        return (-bid.price, bid.time)

    def cancel(self):
        if self.active:
            self.book.cancel_bid(self)
            self.active = False

class Ask(Order):
    @classmethod
    def comparator(cls, ask):
        return (ask.price, ask.time)
    
    def cancel(self):
        if self.active:
            self.book.cancel_ask(self)
            self.active = False

class OrderBook:
    """An order book for Havven agents to interact with.
    This one is generic, but there will have to be three markets in Havven (cur-nom, cur-fiat, nom-fiat)."""

    def __init__(self):
        # An order is a tuple: (price, issue time, quantity, issuer)
        # Buys and sells should be ordered, by price first, then date.

        self.time = 0

        # Bids are ordered highest-first
        self.buy_orders = SortedListWithKey(key=Bid.comparator)
        # Asks are ordered lowest-first
        self.sell_orders = SortedListWithKey(key=Ask.comparator)

    def step(self):
        """Advance the time on this order book by one step."""
        self.time += 1

    def bid(self, price, quantity, agent):
        """Submit a new sell order to the book."""
        self.buy_orders.add(Ask(price, self.time, quantity, agent, self))
        self.step()

    def ask(self, price, quantity, agent):
        """Submit a new buy order to the book."""
        self.sell_orders.add(Ask(price, self.time, quantity, agent, self))
        self.step()
    
    def buy(self, quantity, agent):
        """Buy a quantity at the best available price."""
        self.bid(self.lowest_ask(), quantity, agent)
    
    def sell(self, quantity, agent):
        """Sell a quantity at the best available prices."""
        self.ask(self.highest_bid(), quantity, agent)
    
    def cancel_bid(self, order):
        """Cancel a previously-existing order."""
        self.buy_orders.remove(order)
        self.step()

    def cancel_ask(self, order):
        self.sell_orders.remove(order)
        self.step()
    
    def highest_bid(self) -> float:
        """Return the highest available buy price."""
        return self.buy_orders[0].price
    
    def lowest_ask(self) -> float:
        """Return the lowest available sell price."""
        return self.sell_orders[0].price

    def spread(self) -> float:
        """Return the gap between best buy and sell prices."""
        return self.lowest_ask() - self.highest_bid()

    def resolve(self):
        """Match bids with asks and perform any trades that can be made."""
        pass