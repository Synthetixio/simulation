"""orderbook: an order book for trading in a market."""

from sortedcontainers import SortedListWithKey

class Order:
    """A single order, including price, quantity, and the agent which submitted it."""
    def __init__(self, price, time, quantity, issuer):
        self.price = price
        self.time = time
        self.quantity = quantity
        self.issuer = issuer

class Bid(Order):
    @classmethod
    def comparator(cls, bid):
        return (bid.price, bid.time)

class Ask(Order):
    @classmethod
    def comparator(cls, ask):
        return (-ask.price, ask.time)

class OrderBook:
    """An order book for Havven agents to interact with.
    This one is generic, but there will have to be three markets in Havven (cur-nom, cur-fiat, nom-fiat)."""

    def __init__(self):
        # An order is a tuple: (price, issue time, quantity, issuer)
        # Buys and sells should be ordered, by price first, then date.

        self.time = 0

        # Asks are ordered highest-first
        self.buy_orders = SortedListWithKey(key=Ask.comparator)
        # Bids are ordered lowest-first
        self.sell_orders = SortedListWithKey(key=Bid.comparator)

    def step(self):
        """Advance the time on this order book by one step."""
        self.time += 1

    def ask(self, price, quantity):
        """Submit a new buy order to the book."""
        pass

    def bid(self, price, quantity):
        """Submit a new sell order to the book."""
        pass
    
    def buy(self, quantity):
        """Buy a quantity at the best available price."""
        pass
    
    def sell(self, quantity):
        """Sell a quantity at the best available prices."""
        pass
    
    def cancel_bid(self, order):
        pass

    def cancel_ask(self, order):
        pass
    
    def highest_bid(self):
        """Return the highest available sell price."""
        pass
    
    def lowest_ask(self):
        """Return the lowest available buy price."""
        pass

    def spread(self):
        """Return the gap between best buy and sell prices."""
        return self.lowest_ask() - self.highest_bid()

    def resolve(self):
        """Match bids with asks and perform any trades that can be made."""
        pass