from decimal import Decimal as Dec
from typing import Dict
from itertools import permutations

from managers import HavvenManager as hm
from core.orderbook import OrderBook
from .marketplayer import MarketPlayer


# TODO: consider if arbitrageurs should balance out their currency fractions periodically.

currencies = ['h', 'n', 'f']
market_directions = {
    # what to place to go from a->b
    'h': {'n': 'ask', 'f': 'ask'},
    'n': {'h': 'bid', 'f': 'ask'},
    'f': {'n': 'bid', 'h': 'bid'}
}


class Arbitrageur(MarketPlayer):
    """Wants to find arbitrage cycles and exploit them to equalise prices."""

    def __init__(self, unique_id: int, havven: "model.HavvenModel",
                 fiat: Dec = Dec(0), havvens: Dec = Dec(0),
                 nomins: Dec = Dec(0),
                 profit_threshold: Dec = Dec('0.05')) -> None:

        super().__init__(unique_id, havven, fiat=fiat,
                         havvens=havvens, nomins=nomins)

        self.profit_threshold = profit_threshold
        """
        This arbitrageur will only trade if it can make a profit higher than
        this fraction.
        """
        self.minimal_trade_vol = Dec('0.01')
        self.nomins_to_purchase = Dec(0)
        self.nomin_purchase_order = None
        self.market_data = None

    def setup(self, init_value: Dec):
        self.fiat = init_value*2
        self.model.endow_havvens(self, init_value)
        self.nomins_to_purchase = init_value

    def step(self) -> None:
        """
        Find an exploitable arbitrage cycle.

        The only cycles that exist are HAV -> FIAT -> NOM -> HAV,
        its rotations, and the reverse cycles.
        This bot will consider those and act to exploit the most
        favourable such cycle if the profit available around that
        cycle is better than the profit threshold (including fees).
        """

        if self.nomins_to_purchase > 0:
            if self.nomin_purchase_order:
                self.nomin_purchase_order.cancel()
            self.nomin_purchase_order = self.sell_fiat_for_nomins_with_fee(self.nomins_to_purchase)

        self.compute_market_data()

        for cycle in ['fnh', 'hfn', 'nhf']:
            if self._forward_multiple() > 1 + self.profit_threshold:
                a = cycle[0]
                b = cycle[1]
                c = cycle[2]
                profit, vol_a = self.calculate_cycle_volume(a, b, c)
                if vol_a > self.minimal_trade_vol:
                    print(f"forward, {profit}")
                    self.trade_cycle(vol_a, a, b, c)
                    self.compute_market_data()

        for cycle in ['fhn', 'hnf', 'nfh']:
            if self._reverse_multiple() > 1 + self.profit_threshold:
                a = cycle[0]
                b = cycle[1]
                c = cycle[2]
                profit, vol_a = self.calculate_cycle_volume(a, b, c)
                if vol_a > self.minimal_trade_vol:
                    print(f"reverse, {profit}")
                    self.trade_cycle(vol_a, a, b, c)
                    self.compute_market_data()

    def calculate_cycle_volume(self, a, b, c):
        """
        Calculate the available volume and the profit the a->b->c->a cycle has
        """
        if a == 'h':
            volume = self.available_havvens
        elif a == 'n':
            volume = self.available_nomins
        else:
            volume = self.available_fiat

        profit = 1

        if market_directions[a][b] == 'ask':
            volume = min(
                self.market_data[a][b][1],
                volume
            )
            profit *= self.market_data[a][b][0]
        else:
            volume = min(
                self.market_data[a][b][1]/self.market_data[a][b][0],
                volume
            )
            profit /= self.market_data[a][b][0]

        if market_directions[b][c] == 'ask':
            volume = min(
                self.market_data[b][c][1],
                volume
            )
            profit *= self.market_data[a][b][0]

        else:
            volume = min(
                self.market_data[b][c][1]/self.market_data[b][c][0],
                volume
            )
            profit /= self.market_data[a][b][0]

        if market_directions[c][a] == 'ask':
            volume = min(
                self.market_data[c][a][1],
                volume
            )
            profit *= self.market_data[a][b][0]

        else:
            volume = min(
                self.market_data[c][a][1]/self.market_data[c][a][0],
                volume
            )
            profit /= self.market_data[a][b][0]

        return profit, volume

    def trade_cycle(self, volume, a, b, c):
        """
        Do the trade cycle a->b->c->a, starting the cycle with volume(in terms of a)
        """
        print(f"doing trade {a}-{b}-{c}-{a}")
        initial_volume = volume
        if market_directions[a][b] == 'ask':
            trade = self.market_data[a][b][2].ask(
                self.market_data[a][b][0],
                volume,
                self,
            )
            volume = trade.quantity*trade.price
            print(trade.active, trade)
            trade.cancel()
            print(trade.quantity, trade.price, self.market_data[a][b][0], self.market_data[a][b][1])
        else:
            trade = self.market_data[a][b][2].bid(
                self.market_data[a][b][0],
                volume/self.market_data[a][b][0],
                self
            )
            if trade.active:
                volume = volume/self.market_data[a][b][0] - trade.quantity
            else:
                volume = trade.quantity
            print(trade.active, trade)
            trade.cancel()
            print(trade.quantity, trade.price, self.market_data[a][b][0], self.market_data[a][b][1])

        if market_directions[b][c] == 'ask':
            trade = self.market_data[b][c][2].ask(
                self.market_data[b][c][0],
                volume,
                self
            )
            print(trade.active, trade)
            trade.cancel()
            print(trade.quantity, trade.price, self.market_data[b][c][0], self.market_data[b][c][1])
            volume = trade.quantity*trade.price
        else:
            trade = self.market_data[b][c][2].bid(
                self.market_data[b][c][0],
                volume/self.market_data[b][c][0],
                self
            )
            print(trade.active, trade)
            trade.cancel()
            print(trade.quantity, trade.price, self.market_data[b][c][0], self.market_data[b][c][1])
            volume = trade.quantity

        if market_directions[c][a] == 'ask':
            trade = self.market_data[c][a][2].ask(
                self.market_data[c][a][0],
                volume,
                self
            )
            print(trade.active, trade)
            trade.cancel()
            print(trade.quantity, trade.price, self.market_data[c][a][0], self.market_data[c][a][1])
            volume = trade.quantity*trade.price
        else:
            trade = self.market_data[c][a][2].bid(
                self.market_data[c][a][0],
                volume/self.market_data[c][a][0],
                self
            )
            print(trade.active, trade)
            trade.cancel()
            print(trade.quantity, trade.price, self.market_data[c][a][0], self.market_data[c][a][1])
            volume = trade.quantity
        print(f'profited {volume - initial_volume}{a}\n===')

    def _cycle_fee_rate(self) -> Dec:
        """Divide by this fee rate to determine losses after one traversal of an arbitrage cycle."""
        return hm.round_decimal((Dec(1) + self.model.fee_manager.nomin_fee_rate) *
                                (Dec(1) + self.model.fee_manager.havven_fee_rate) *
                                (Dec(1) + self.model.fee_manager.fiat_fee_rate))

    def _forward_multiple_no_fees(self) -> Dec:
        """
        The value multiple after one forward arbitrage cycle, neglecting fees.
        """
        # hav -> fiat -> nom -> hav
        return hm.round_decimal(self.havven_fiat_market.highest_bid_price() /
                                (self.nomin_fiat_market.lowest_ask_price() *
                                 self.havven_nomin_market.lowest_ask_price()))

    def _reverse_multiple_no_fees(self) -> Dec:
        """
        The value multiple after one reverse arbitrage cycle, neglecting fees.
        """
        # hav -> nom -> fiat -> hav
        return hm.round_decimal((self.havven_nomin_market.highest_bid_price() *
                                 self.nomin_fiat_market.highest_bid_price()) /
                                self.havven_fiat_market.lowest_ask_price())

    def _forward_multiple(self) -> Dec:
        """The return after one forward arbitrage cycle."""
        # Note, this only works because the fees are purely multiplicative.
        return hm.round_decimal(self._forward_multiple_no_fees() / self._cycle_fee_rate())

    def _reverse_multiple(self) -> Dec:
        """The return after one reverse arbitrage cycle."""
        # As above. If the fees were not just levied as percentages this would need to be updated.
        return hm.round_decimal(self._reverse_multiple_no_fees() / self._cycle_fee_rate())

    def compute_market_data(self) -> None:
        self.market_data = {
            # what to buy into to go a->b instantly
            'h': {
                'f': [self.havven_fiat_market.highest_bid_price(),
                      self.havven_fiat_market.highest_bid_quantity(),
                      self.havven_fiat_market],
                'n': [self.havven_nomin_market.highest_bid_price(),
                      self.havven_nomin_market.highest_bid_quantity(),
                      self.havven_nomin_market]
            },
            'n': {
                'h': [self.havven_nomin_market.lowest_ask_price(),
                      self.havven_nomin_market.lowest_ask_quantity(),
                      self.havven_nomin_market],
                'f': [self.nomin_fiat_market.highest_bid_price(),
                      self.nomin_fiat_market.highest_bid_quantity(),
                      self.nomin_fiat_market]
            },
            'f': {
                'h': [self.havven_fiat_market.lowest_ask_price(),
                      self.havven_fiat_market.lowest_ask_quantity(),
                      self.havven_fiat_market],
                'n': [self.nomin_fiat_market.lowest_ask_price(),
                      self.nomin_fiat_market.lowest_ask_quantity(),
                      self.nomin_fiat_market]
            }
        }