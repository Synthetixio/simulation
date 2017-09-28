"""orderbook: an order book for trading in a market."""

# TODO: Convert this all to use python's Decimal representation

# We need a fast ordered data structure in order to support efficient insertion and deletion of orders.
from sortedcontainers import SortedListWithKey
import model

class Order:
    """A single order, including price, quantity, and the agent which submitted it."""
    def __init__(self, price:float, time:int, quantity:float, issuer:"MarketPlayer", book:"OrderBook"):
        self.price = price
        self.time = time
        self.quantity = quantity
        self.issuer = issuer
        self.book = book
        self.active = True
    
    def update_quantity(self, quantity:float):
        if quantity >= 0:
            self.quantity = quantity
        else:
            self.quantity = 0
            self.cancel()
    
    def __str__(self):
        return f"{self.quantity}x{self.price} @ {self.time} by {self.issuer.unique_id}"

class Bid(Order):
    """A bid order. Instantiating one of these will automatically add it to its order book."""
    def __init__(self, price:float, quantity:float, issuer:"MarketPlayer", book:"OrderBook"):
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

    def cancel(self):
        if self.active:
            self.active = False
            self.book.buy_orders.remove(self)
            self.book.step()
            self.issuer.orders.remove(self)
            self.issuer.notify_cancelled(self)

    def update_price(self, price:float):
        if self.active:
            self.book.buy_orders.remove(order)
            self.price = price
            self.time = self.book.time
            self.book.buy_orders.add(order)
            self.book.step()
    
    def __str__(self):
        return "Bid: " + super().__str__()


class Ask(Order):
    """An ask order. Instantiating one of these will automatically add it to its order book."""
    def __init__(self, price:float, quantity:float, issuer:"MarketPlayer", book:"OrderBook"):
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

    def cancel(self):
        if self.active:
            self.active = False
            self.book.sell_orders.remove(self)
            self.book.step()
            self.issuer.orders.remove(self)
            self.issuer.notify_cancelled(self)

    def update_price(self, price:float):
        if self.active:
            self.book.sell_orders.remove(order)
            self.price = price
            self.time = self.book.time
            self.book.sell_orders.add(order)
            self.book.step()

    def __str__(self):
        return "Ask: " + super().__str__()

class OrderBook:
    """An order book for Havven agents to interact with.
    This one is generic, but there will have to be three markets in Havven (nom-cur, fiat-cur, fiat-nom)."""

    def __init__(self, name, match):
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
        self.match = match

    def step(self):
        """Advance the time on this order book by one step."""
        self.time += 1

    def bid(self, price:float, quantity:float, agent:"MarketPlayer") -> Bid:
        """Submit a new sell order to the book."""
        return Bid(price, quantity, agent, self)

    def ask(self, price:float, quantity:float, agent:"MarketPlayer") -> Ask:
        """Submit a new buy order to the book."""
        return Ask(price, quantity, agent, self)
    
    def buy(self, quantity:float, agent:"MarketPlayer", premium=0) -> Bid:
        """Buy a quantity of the sale token at the best available price."""
        lowest_ask = self.lowest_ask()
        price = (self.price if lowest_ask is None else lowest_ask) + premium
        return self.bid(price, quantity, agent)
    
    def sell(self, quantity:float, agent:"MarketPlayer", discount=0) -> Ask:
        """Sell a quantity of the sale token at the best available price."""
        highest_bid = self.highest_bid()
        price = (self.price if highest_bid is None else highest_bid) - discount
        return self.ask(price, quantity, agent)
    
    def highest_bid(self) -> float:
        """Return the highest available buy price."""
        return self.buy_orders[0].price if len(self.buy_orders) else self.price
    
    def lowest_ask(self) -> float:
        """Return the lowest available sell price."""
        return self.sell_orders[0].price if len(self.sell_orders) else self.price

    def spread(self) -> float:
        """Return the gap between best buy and sell prices."""
        return self.lowest_ask() - self.highest_bid()
    
    def resolve(self):
        """Match bids with asks and perform any trades that can be made."""
        prev_bid, prev_ask = None, None
        spread = 0
        # Repeatedly match the best pair of orders until no more matches can succeed.
        # Finish if there there are no orders left, or if the last match failed to remove any orders
        # This relies upon the bid and ask books being maintained ordered.
        while spread <= 0 and len(self.buy_orders) and len(self.sell_orders) and \
              not (prev_bid == self.buy_orders[0] and prev_ask == self.sell_orders[0]):
            prev_bid, prev_ask = self.buy_orders[0], self.sell_orders[0]
            self.match(prev_bid, prev_ask)
            spread = self.spread()