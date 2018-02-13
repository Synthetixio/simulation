from decimal import Decimal as Dec
from typing import Dict, List, Any, NamedTuple
import pprint
from collections import namedtuple

from managers import HavvenManager as hm
from core import model
from .marketplayer import MarketPlayer

from core import orderbook as ob

nom = 'nom'
hav = 'hav'
fiat = 'fiat'

MarketData: NamedTuple = namedtuple("MarketData", ["price", "quantity", "market"])

market_directions = {
    # what to place to go from a->b
    hav: {nom: 'ask', fiat: 'ask'},
    nom: {hav: 'bid', fiat: 'ask'},
    fiat: {nom: 'bid', hav: 'bid'}
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
        self.minimal_trade_vol: Dec = Dec('0.01')
        self.nomins_to_purchase: Dec = Dec(0)
        self.nomin_purchase_order: ob.LimitOrder = None
        self.market_data: Dict[str, Dict[str, MarketData]] = None
        self.min_fiat: Dec = None

    def setup(self, wealth_parameter: Dec, wage_parameter: Dec, liquidation_param: Dec) -> None:
        super().setup(wealth_parameter, wage_parameter, liquidation_param)
        self.min_fiat = wealth_parameter
        self.fiat = wealth_parameter * 2
        self.model.endow_havvens(self, wealth_parameter)
        self.nomins_to_purchase = wealth_parameter

    def step(self) -> None:
        """
        Find an exploitable arbitrage cycle.

        The only cycles that exist are HAV -> FIAT -> NOM -> HAV,
        its rotations, and the reverse cycles.
        This bot will consider those and act to exploit the most
        favourable such cycle if the profit available around that
        cycle is better than the profit threshold (including fees).
        """
        super().step()

        if self.nomins_to_purchase > 0:
            if self.nomin_purchase_order:
                self.nomin_purchase_order.cancel()
            if self.available_fiat > self.min_fiat:
                self.nomin_purchase_order = self.sell_fiat_for_nomins_with_fee(self.nomins_to_purchase)
            else:
                self.nomins_to_purchase = Dec(0)

        self.compute_market_data()

        for cycle in [(fiat, nom, hav), (hav, fiat, nom), (nom, hav, fiat)]:
            if self._forward_multiple() > 1 + self.profit_threshold:
                a, b, c = cycle
                vol_a = self.calculate_cycle_volume(a, b, c)
                if vol_a > self.minimal_trade_vol:
                    try:
                        self.trade_cycle(vol_a, a, b, c)
                    except AttributeError:
                        # one of the trades didn't go through, just ignore
                        pass
                    self.compute_market_data()

        for cycle in [(fiat, hav, nom), (hav, nom, fiat), (nom, fiat, hav)]:
            if self._reverse_multiple() > 1 + self.profit_threshold:
                a, b, c = cycle
                vol_a = self.calculate_cycle_volume(a, b, c)
                if vol_a > self.minimal_trade_vol:
                    try:
                        self.trade_cycle(vol_a, a, b, c)
                    except AttributeError:
                        # one of the trades didn't go through, just ignore
                        pass
                    self.compute_market_data()
                else:
                    # don't try again if volume is too low
                    break

    def calculate_cycle_volume(self, a, b, c) -> Dec:
        """
        Calculate the available volume and the profit the a->b->c->a cycle has

        TODO: ensure correctness of volume calculation. Seems to work but looks wrong...
        """

        if a == hav:
            volume = self.available_havvens
        elif a == nom:
            volume = self.available_nomins
        elif a == fiat:
            volume = self.available_fiat
        else:
            raise Exception(f"{a} is not in [{hav}, {nom}, {fiat}]")

        if market_directions[a][b] == 'ask':
            volume = min(
                self.market_data[a][b].quantity * self.market_data[a][b].price,
                volume / self.market_data[a][b].price
            )
        else:
            volume = min(
                self.market_data[a][b].quantity,
                volume / self.market_data[a][b].price
            )

        if market_directions[b][c] == 'ask':
            volume = min(
                self.market_data[b][c].quantity * self.market_data[b][c].price,
                volume / self.market_data[b][c].price
            )
        else:
            volume = min(
                self.market_data[b][c].quantity,
                volume / self.market_data[b][c].price
            )

        if market_directions[c][a] == 'ask':
            volume = min(
                self.market_data[c][a].quantity * self.market_data[b][c].price,
                volume / self.market_data[c][a].price
            )
        else:
            volume = min(
                self.market_data[c][a].quantity,
                volume * self.market_data[b][c].price
            )
        return volume

    def trade_cycle(self, volume, a, b, c) -> None:
        """
        Do the trade cycle a->b->c->a, starting the cycle with volume(in terms of a)
        """

        init_havvens = self.havvens
        init_nomins = self.nomins
        init_fiat = self.fiat

        initial_wealth = self.wealth()

        if market_directions[a][b] == 'ask':
            trade = self.market_data[a][b].market.ask(
                self.market_data[a][b].price,
                volume,
                self,
            )
            volume = (trade.initial_quantity - trade.quantity) * trade.price
            trade.cancel()
        else:
            trade = self.market_data[a][b].market.bid(
                self.market_data[a][b].price,
                volume / self.market_data[a][b].price,
                self
            )
            volume = (trade.initial_quantity - trade.quantity)
            trade.cancel()

        if market_directions[b][c] == 'ask':
            trade = self.market_data[b][c].market.ask(
                self.market_data[b][c].price,
                volume,
                self
            )
            volume = (trade.initial_quantity - trade.quantity) * trade.price
            trade.cancel()
        else:
            trade = self.market_data[b][c].market.bid(
                self.market_data[b][c].price,
                volume / self.market_data[b][c].price,
                self
            )
            volume = (trade.initial_quantity - trade.quantity)
            trade.cancel()

        if market_directions[c][a] == 'ask':
            trade = self.market_data[c][a].market.ask(
                self.market_data[c][a].price,
                volume,
                self
            )
            trade.cancel()
        else:
            trade = self.market_data[c][a].market.bid(
                self.market_data[c][a].price,
                volume / self.market_data[c][a].price,
                self
            )
            trade.cancel()
        if (self.wealth() - initial_wealth) < 0:
            print("----------")
            print("- Error with arbitrageur, didn't profit on cycle. Made:")
            print(f'- {self.nomins - init_nomins}n')
            print(f'- {self.havvens - init_havvens}h')
            print(f'- {self.fiat - init_fiat}f')
            print(f'- {initial_wealth} -> {self.wealth()}')
            print(f'- {self.escrowed_havvens}')
            print(f'- {self.issued_nomins}')
            print(f'- profited {self.wealth() - initial_wealth} on {a}-{b}-{c}-{a}')
            print("----------")

    def _cycle_fee_rate(self) -> Dec:
        """Divide by this fee rate to determine losses after one traversal of an arbitrage cycle."""
        return hm.round_decimal((Dec(1) + self.model.fee_manager.nomin_transfer_fee_rate) *
                                (Dec(1) + self.model.fee_manager.havven_transfer_fee_rate) *
                                (Dec(1) + self.model.fee_manager.fiat_transfer_fee_rate))

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
            hav: {
                fiat: MarketData(
                    self.havven_fiat_market.highest_bid_price(),
                    self.havven_fiat_market.highest_bid_quantity(),
                    self.havven_fiat_market
                ),
                nom: MarketData(
                    self.havven_nomin_market.highest_bid_price(),
                    self.havven_nomin_market.highest_bid_quantity(),
                    self.havven_nomin_market
                )
            },
            nom: {
                hav: MarketData(
                    self.havven_nomin_market.lowest_ask_price(),
                    self.havven_nomin_market.lowest_ask_quantity(),
                    self.havven_nomin_market
                ),
                fiat: MarketData(
                    self.nomin_fiat_market.highest_bid_price(),
                    self.nomin_fiat_market.highest_bid_quantity(),
                    self.nomin_fiat_market
                )
            },
            fiat: {
                hav: MarketData(
                    self.havven_fiat_market.lowest_ask_price(),
                    self.havven_fiat_market.lowest_ask_quantity(),
                    self.havven_fiat_market
                ),
                nom: MarketData(
                    self.nomin_fiat_market.lowest_ask_price(),
                    self.nomin_fiat_market.lowest_ask_quantity(),
                    self.nomin_fiat_market
                )
            }
        }
