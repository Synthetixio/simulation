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

class Bid(Order):
    @classmethod
    def comparator(cls, bid:"Bid"):
        return (-bid.price, bid.time)

    def cancel(self):
        self.book.cancel_bid(self)
        self.issuer.cancel_order(self)

    def update_price(self, price:float):
        self.book.update_bid_price(price, quantity)

class Ask(Order):
    @classmethod
    def comparator(cls, ask:"Ask"):
        return (ask.price, ask.time)
    
    def cancel(self):
        self.book.cancel_ask(self)
        self.issuer.cancel_order(self)

    def update_price(self, price:float):
        self.book.update_ask_price(price)

class OrderBook:
    """An order book for Havven agents to interact with.
    This one is generic, but there will have to be three markets in Havven (cur-nom, cur-fiat, nom-fiat)."""

    def __init__(self, match):
        # Buys and sells should be ordered, by price first, then date.
        # Bids are ordered highest-first
        self.buy_orders = SortedListWithKey(key=Bid.comparator)
        # Asks are ordered lowest-first
        self.sell_orders = SortedListWithKey(key=Ask.comparator)

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
        order = self.buy_orders.add(Ask(price, self.time, quantity, agent, self))
        self.step()
        return order

    def ask(self, price:float, quantity:float, agent:"MarketPlayer") -> Ask:
        """Submit a new buy order to the book."""
        order = self.sell_orders.add(Ask(price, self.time, quantity, agent, self))
        self.step()
        return order
    
    def buy(self, quantity:float, agent:"MarketPlayer") -> Bid:
        """Buy a quantity at the best available price."""
        lowest_ask = self.lowest_ask()
        return self.bid(self.price if lowest_ask is None else lowest_ask, quantity, agent)
    
    def sell(self, quantity:float, agent:"MarketPlayer") -> Ask:
        """Sell a quantity at the best available prices."""
        highest_bid = self.highest_bid()
        return self.ask(self.price if highest_bid is None else highest_bid, quantity, agent)
    
    def cancel_bid(self, order:Order):
        """Cancel a previously-existing order."""
        self.buy_orders.remove(order)
        order.active = False
        self.step()

    def cancel_ask(self, order:Order):
        self.sell_orders.remove(order)
        order.active = False
        self.step()

    def update_bid_price(self, order:Order, price:float):
        self.buy_orders.remove(order)
        order.price = price
        order.time = self.time
        self.buy_orders.add(order)
        self.step()

    def update_ask_price(self, order:Order, price:float):
        self.sell_orders.remove(order)
        order.price = price
        order.time = self.time
        self.sell_orders.add(order)
        self.step()
    
    def highest_bid(self) -> float:
        """Return the highest available buy price."""
        return self.buy_orders[0].price if len(self.buy_orders) else None
    
    def lowest_ask(self) -> float:
        """Return the lowest available sell price."""
        return self.sell_orders[0].price if len(self.sell_orders) else None

    def spread(self) -> float:
        """Return the gap between best buy and sell prices."""
        lowest_ask, highest_bid = self.lowest_ask(), self.highest_bid()
        if lowest_ask is None or highest_bid is None:
            return None
        return lowest_ask - highest_bid
    
    def resolve(self):
        """Match bids with asks and perform any trades that can be made."""
        prev_bid, prev_ask = None, None
        spread = None
        # Repeatedly match the best pair of orders until no more matches can succeed.
        # Finish if there there are no orders left, or if the last match failed to remove any orders
        # This relies upon the bid and ask books being maintained ordered.
        while spread is not None and spread <= 0 and \
              not (prev_bid == self.buy_orders[0] and prev_ask == self.sell_orders[0]):
            prev_bid, prev_ask = self.buy_orders[0], self.sell_orders[0]
            self.match(prev_bid, prev_ask)
            spread = self.spread()