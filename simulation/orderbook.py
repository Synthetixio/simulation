class Order:
    """A single order, including price, quantity, and the agent which submitted it."""
    def __init__(self, price, quantity, issuer):
        self.price = price
        self.quantity = quantity
        self.issuer = issuer


class OrderBook:
    """An order book for Havven agents to interact with.
    This one is generic, but there will have to be three (CUR-NOM, CUR-fiat, NOM-fiat)."""

    def __init__(self):
        # Buys and sells should be maintained in order, price first, then date.
        # It might be that we want to change these to linked lists for efficient order cancellation.
        self.buy_orders = []
        self.sell_orders = []

    def ask(self, price, quantity):
        """Submit a new buy order to the book."""
        pass

    def bid(self, price, quantity):
        """Submit a new sell order to the book."""
        pass
    
    def market_ask(self, quantity):
        """Buy a quantity at the best available price."""
        pass
    
    def market_bid(self, quantity):
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
