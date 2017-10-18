"""orderbook: an order book for trading in a market."""

from typing import Iterable, Callable, List, Optional
from itertools import takewhile
from decimal import Decimal as Dec

# We need a fast ordered data structure to support efficient insertion and deletion of orders.
from sortedcontainers import SortedListWithKey, SortedDict

import agents as ag

from managers import HavvenManager


class LimitOrder:
    """A single limit order, including price, quantity, the issuer, and orderbook it belongs to."""
    def __init__(self, price: Dec, time: int, quantity: Dec, fee: Dec,
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

    def update_price(self, price: Dec, fee: Dec) -> None:
        """Update this order's price, updating its timestamp, possibly reordering its order book."""
        pass

    def update_quantity(self, quantity: Dec, fee: Dec) -> None:
        """Update the quantity of this order, cancelling it if the quantity is not positive."""
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
        if quantity <= 0:
            self.active = False  # bid will not be added to the orderbook
        else:
            self.book.add_new_bid(self)

    @classmethod
    def comparator(cls, bid: "Bid"):
        """Bids are sorted first by descending price and then by ascending time."""
        return -bid.price, bid.time

    def cancel(self) -> None:
        if self.active:
            self.active = False
            self.book.remove_from_bids(self)
        self.quantity = Dec(0)
        self.fee = Dec(0)

    def update_price(self, price: Dec, fee: Dec) -> None:
        if self.active:
            self.book.update_bid(self, price, self.quantity, fee)
            self.time = self.book.time

    def update_quantity(self, quantity: Dec, fee: Dec):
        if quantity > 0:
            self.book.update_bid(self, self.price, quantity, fee)
        else:
            self.cancel()

    def __str__(self) -> str:
        return "Bid: " + super().__str__()


class Ask(LimitOrder):
    """An ask order. Instantiating one of these will automatically add it to its order book."""
    def __init__(self, price: Dec, quantity: Dec, fee: Dec,
                 issuer: "ag.MarketPlayer", book: "OrderBook") -> None:
        super().__init__(price, book.time, quantity, fee, issuer, book)
        if quantity <= 0:
            self.active = False  # ask will not be added to the orderbook
        else:
            self.book.add_new_ask(self)

    @classmethod
    def comparator(cls, ask: "Ask"):
        """Asks are sorted first by ascending price and then by ascending time."""
        return ask.price, ask.time

    def cancel(self) -> None:
        if self.active:
            self.active = False
            self.book.remove_from_asks(self)
        self.quantity = Dec(0)
        self.fee = Dec(0)

    def update_price(self, price: Dec, fee: Dec) -> None:
        if self.active:
            self.book.update_ask(self, price, self.quantity, fee)
            self.time = self.book.time

    def update_quantity(self, quantity: Dec, fee: Dec):
        if quantity > 0:
            self.book.update_ask(self, self.price, quantity, fee)
        else:
            self.cancel()

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
        self.bid_fee_fn: Callable[[Dec], Dec] = bid_fee_fn
        self.ask_fee_fn: Callable[[Dec], Dec] = ask_fee_fn

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

    def bid(self, price: Dec, quantity: Dec, agent: "ag.MarketPlayer") -> Optional[Bid]:
        """
        Submit a new sell order to the book.
        """
        fee = self.bid_fee_fn(price * quantity)

        if agent.__dict__[self.quote] - agent.__dict__["used_"+self.quote] < quantity + fee:
            return None

        bid = Bid(HavvenManager.round_decimal(price), HavvenManager.round_decimal(quantity),
                  HavvenManager.round_decimal(fee), agent, self)
        if self.match_on_order:
            self.match()
        return bid

    def ask(self, price: Dec, quantity: Dec, agent: "ag.MarketPlayer") -> Optional[Ask]:
        """
        Submit a new buy order to the book.
        """
        fee = self.ask_fee_fn(quantity)

        if agent.__dict__[self.base] - agent.__dict__["used_"+self.base] < quantity + fee:
            return None

        ask = Ask(HavvenManager.round_decimal(price), HavvenManager.round_decimal(quantity),
                  HavvenManager.round_decimal(fee), agent, self)
        if self.match_on_order:
            self.match()
        return ask

    def buy(self, quantity: Dec, agent: "ag.MarketPlayer", premium: Dec = Dec('0.0')) -> Bid:
        """
        Buy a quantity of the sale token at the best available price.
        Optionally buy at a premium a certain fraction above the market price.
        """
        price = self.price_to_buy_quantity(quantity) * (Dec(1) + premium)
        return self.bid(price, quantity, agent)

    def sell(self, quantity: Dec, agent: "ag.MarketPlayer", discount: Dec = Dec('0.0')) -> Ask:
        """
        Sell a quantity of the sale token at the best available price.
        Optionally sell at a discount a certain fraction below the market price.
        """
        price = self.price_to_sell_quantity(quantity) * (Dec(1) - discount)
        return self.ask(price, quantity, agent)

    def price_to_buy_quantity(self, quantity: Dec) -> Dec:
        """
        The bid price to buy a certain quantity, ignoring fees.
        Note that this is an instantaneous metric which may be
          invalidated if intervening trades are made.
        TODO: handle the null case properly, not just use self.price
        """
        cumulative = Dec(0)
        price = self.price
        for price in self.ask_quants:
            cumulative += self.ask_quants[price]
            if cumulative >= quantity:
                break
        return price

    def price_to_sell_quantity(self, quantity: Dec) -> Dec:
        """
        The ask price to sell a certain quantity, ignoring fees.
        Note that this is an instantaneous metric which may be
          invalidated if intervening trades are made.
        TODO: handle the null case properly, not just use self.price
        """
        cumulative = Dec(0)
        price = self.price
        for price in self.bid_quants:
            cumulative += self.bid_quants[price]
            if cumulative >= quantity:
                break
        return price

    def bids_higher_or_equal(self, price: Dec) -> Iterable[Bid]:
        """Return an iterator of bids whose prices are no lower than the given price."""
        return takewhile(lambda bid: bid.price >= price, self.bids)

    def highest_bid_price(self) -> Dec:
        """Return the highest available buy price."""
        return self.bids[0].price if (len(self.bids) > 0) else self.price

    def highest_bids(self) -> Iterable[Bid]:
        """Return the list of highest-priced bids. May be empty if there are none."""
        return self.bids_higher_or_equal(self.highest_bid_price())

    def asks_lower_or_equal(self, price: Dec) -> Iterable[Bid]:
        """Return an iterator of asks whose prices are no higher than the given price."""
        return takewhile(lambda ask: ask.price <= price, self.asks)

    def lowest_ask_price(self) -> Dec:
        """Return the lowest available sell price."""
        return self.asks[0].price if (len(self.asks) > 0) else self.price

    def lowest_asks(self) -> Iterable[Bid]:
        """Return the list of lowest-priced asks. May be empty if there are none."""
        return self.asks_lower_or_equal(self.lowest_ask_price())

    def spread(self) -> Dec:
        """Return the gap between best buy and sell prices."""
        return self.lowest_ask_price() - self.highest_bid_price()

    def add_new_bid(self, bid):
        """add a new bid"""
        bid.issuer.orders.add(bid)
        self.bids.add(bid)
        if bid.price in self.bid_quants:
            self.bid_quants[bid.price] += bid.quantity
        else:
            self.bid_quants[bid.price] = bid.quantity
        self.step()

    def update_bid(self, bid, new_price, new_quantity, new_fee):
        """
        Update cached bid quantity if price or quantity change
        This won't work for new bid/ask
        """
        if bid.price == new_price:
            if new_price in self.bid_quants:
                self.bid_quants[new_price] += (new_quantity - bid.quantity)
            else:
                self.bid_quants[new_price] = new_quantity
            # price remains the same, so position doesn't need to update
            bid.price = new_price
            bid.quantity = new_quantity
            bid.fee = new_fee
        else:
            if self.bid_quants[bid.price] == bid.quantity:
                self.bid_quants.pop(bid.price)
            else:
                self.bid_quants[bid.price] -= bid.quantity
            self.bid_quants[new_price] = new_quantity

            # update bid position in list
            self.bids.pop(bid)
            bid.price = new_price
            bid.quantity = new_quantity
            bid.fee = new_fee
            self.bids.add(bid)

            # only update the bid time if the price changed
            bid.time = self.time
        self.step()

    def remove_from_bids(self, bid):
        """Remove a bid from the bid list, and update cached quantity"""
        self.bids.remove(bid)
        if self.bid_quants[bid.price] == bid.quantity:
            self.bid_quants.pop(bid.price)
        else:
            self.bid_quants[bid.price] -= bid.quantity
        self.step()
        bid.issuer.orders.remove(bid)
        bid.issuer.notify_cancelled(bid)

    def add_new_ask(self, ask):
        """add a new ask"""
        ask.issuer.orders.add(ask)
        self.asks.add(ask)
        if ask.price in self.ask_quants:
            self.ask_quants[ask.price] += ask.quantity
        else:
            self.ask_quants[ask.price] = ask.quantity
        self.step()

    def update_ask(self, ask, new_price, new_quantity, new_fee):
        """
        Update cached ask quantity if price or quantity change
        This won't work for new ask/ask
        """
        if ask.price == new_price:
            if new_price in self.ask_quants:
                self.ask_quants[new_price] += (new_quantity - ask.quantity)
            else:
                self.ask_quants[new_price] = new_quantity
            # price remains the same, so position doesn't need to update
            ask.price = new_price
            ask.quantity = new_quantity
            ask.fee = new_fee
        else:
            if self.ask_quants[ask.price] == ask.quantity:
                self.ask_quants.pop(ask.price)
            else:
                self.ask_quants[ask.price] -= ask.quantity
            self.ask_quants[new_price] = new_quantity

            # update ask position in list
            self.asks.pop(ask)
            ask.price = new_price
            ask.quantity = new_quantity
            ask.fee = new_fee
            self.asks.add(ask)

            # only update the ask time if the price changed
            ask.time = self.time
        self.step()

    def remove_from_asks(self, ask):
        """Remove an ask from the ask list, and update cached quantity"""
        self.asks.remove(ask)

        if self.ask_quants[ask.price] == ask.quantity:
            self.ask_quants.pop(ask.price)
        else:
            self.ask_quants[ask.price] -= ask.quantity
        self.step()
        ask.issuer.orders.remove(ask)
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

            spread = self.spread()

        self.price = (self.lowest_ask_price() + self.highest_bid_price()) / 2
