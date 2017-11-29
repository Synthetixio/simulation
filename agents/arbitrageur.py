from typing import Dict
from decimal import Decimal as Dec

from .marketplayer import MarketPlayer

from managers import HavvenManager as hm
from orderbook import OrderBook


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

        # Cached values of the amount available in arb cycles for performance
        # and neatness.
        self.havven_fiat_bid_qty = Dec(0)
        self.havven_nomin_bid_qty = Dec(0)
        self.nomin_fiat_bid_qty = Dec(0)
        self.nomin_fiat_ask_qty = Dec(0)
        self.havven_nomin_ask_qty = Dec(0)
        self.havven_fiat_ask_qty = Dec(0)

    def setup(self, init_value: Dec):
        self.fiat = init_value
        self.model.endow_havvens(self, init_value)

    def step(self) -> None:
        """
        Find an exploitable arbitrage cycle.

        The only cycles that exist are HAV -> FIAT -> NOM -> HAV,
        its rotations, and the reverse cycles.
        This bot will consider those and act to exploit the most
        favourable such cycle if the profit available around that
        cycle is better than the profit threshold (including fees).
        """

        self.havven_fiat_bid_qty = self.havven_fiat_market.highest_bid_quantity()
        self.havven_nomin_bid_qty = self.havven_nomin_market.highest_bid_quantity()
        self.nomin_fiat_bid_qty = self.nomin_fiat_market.highest_bid_quantity()
        self.nomin_fiat_ask_qty = hm.round_decimal(self.nomin_fiat_market.lowest_ask_quantity()
                                                   * self.nomin_fiat_market.lowest_ask_price())
        self.havven_nomin_ask_qty = hm.round_decimal(self.havven_nomin_market.lowest_ask_quantity()
                                                    * self.havven_nomin_market.lowest_ask_price())
        self.havven_fiat_ask_qty = hm.round_decimal(self.havven_fiat_market.lowest_ask_quantity()
                                                   * self.havven_fiat_market.lowest_ask_price())

        wealth = self.wealth()

        # Consider the forward direction
        cc_net_wealth = self.model.fiat_value(**self.forward_havven_cycle_balances()) - wealth
        nn_net_wealth = self.model.fiat_value(**self.forward_nomin_cycle_balances()) - wealth
        ff_net_wealth = self.model.fiat_value(**self.forward_fiat_cycle_balances()) - wealth
        max_net_wealth = max(cc_net_wealth, nn_net_wealth, ff_net_wealth)

        if max_net_wealth > self.profit_threshold:
            if cc_net_wealth == max_net_wealth:
                self.forward_havven_cycle_trade()
            elif nn_net_wealth == max_net_wealth:
                self.forward_nomin_cycle_trade()
            else:
                self.forward_fiat_cycle_trade()

        # Now the reverse direction
        cc_net_wealth = self.model.fiat_value(**self.reverse_havven_cycle_balances()) - wealth
        nn_net_wealth = self.model.fiat_value(**self.reverse_nomin_cycle_balances()) - wealth
        ff_net_wealth = self.model.fiat_value(**self.reverse_fiat_cycle_balances()) - wealth
        max_net_wealth = max(cc_net_wealth, nn_net_wealth, ff_net_wealth)

        if max_net_wealth > self.profit_threshold:
            if cc_net_wealth == max_net_wealth:
                self.reverse_havven_cycle_trade()
            elif nn_net_wealth == max_net_wealth:
                self.reverse_nomin_cycle_trade()
            else:
                self.reverse_fiat_cycle_trade()

    @staticmethod
    def _base_to_quoted_yield(market: OrderBook, base_capital: Dec) -> Dec:
        """
        The quantity of the quoted currency you could obtain at the current
        best market price, selling a given quantity of the base currency.
        """
        price = market.highest_bid_price()
        feeless_capital = market.base_qty_rcvd(base_capital)
        return market.bids_not_lower_quoted_quantity(price, feeless_capital)

    @staticmethod
    def _quoted_to_base_yield(market: OrderBook, quoted_capital: Dec) -> Dec:
        """
        The quantity of the base currency you could obtain at the current
        best market price, selling a given quantity of the quoted currency.
        """
        price = market.lowest_ask_price()
        feeless_capital = market.quoted_qty_rcvd(quoted_capital)
        return market.asks_not_higher_base_quantity(price, feeless_capital)

    def havven_to_fiat_yield(self, capital: Dec) -> Dec:
        """
        The quantity of fiat obtained, spending a quantity of havvens.
        """
        return self._base_to_quoted_yield(self.havven_fiat_market, capital)

    def fiat_to_havven_yield(self, capital: Dec) -> Dec:
        """
        The quantity of havvens obtained, spending a quantity of fiat.
        """
        return self._quoted_to_base_yield(self.havven_fiat_market, capital)

    def havven_to_nomin_yield(self, capital: Dec) -> Dec:
        """
        The quantity of nomins obtained, spending a quantity of havvens.
        """
        return self._base_to_quoted_yield(self.havven_nomin_market, capital)

    def nomin_to_havven_yield(self, capital: Dec) -> Dec:
        """
        The quantity of havvens obtained, spending a quantity of nomins.
        """
        return self._quoted_to_base_yield(self.havven_nomin_market, capital)

    def nomin_to_fiat_yield(self, capital: Dec) -> Dec:
        """
        The quantity of fiat obtained, spending a quantity of nomins.
        """
        return self._base_to_quoted_yield(self.nomin_fiat_market, capital)

    def fiat_to_nomin_yield(self, capital: Dec) -> Dec:
        """
        The quantity of nomins obtained, spending a quantity of fiat.
        """
        return self._quoted_to_base_yield(self.nomin_fiat_market, capital)

    def forward_havven_cycle_balances(self) -> Dict[str, Dec]:
        """
        Return the estimated wallet balances of this agent after
        one forward havven arbitrage cycle: havvens -> fiat -> nomins -> havvens.
        """
        havvens = self.havvens
        nomins = self.nomins
        fiat = self.fiat

        c_qty = min(havvens, self.havven_fiat_bid_qty)
        havvens -= c_qty
        f_qty = self.havven_to_fiat_yield(c_qty)
        fiat += f_qty
        f_qty = min(f_qty, self.nomin_fiat_ask_qty)
        fiat -= f_qty
        n_qty = self.fiat_to_nomin_yield(f_qty)
        nomins += n_qty
        n_qty = min(n_qty, self.havven_nomin_ask_qty)
        nomins -= n_qty
        c_qty = self.nomin_to_havven_yield(n_qty)
        havvens += c_qty

        return {"havvens": havvens, "nomins": nomins, "fiat": fiat}

    def forward_havven_cycle_trade(self) -> None:
        """
        Perform a single forward havven arbitrage cycle;
        havvens -> fiat -> nomins -> havvens.
        """
        c_qty = min(self.available_havvens, self.havven_fiat_bid_qty)
        pre_fiat = self.fiat
        self.sell_havvens_for_fiat_with_fee(c_qty)
        f_qty = min(self.fiat - pre_fiat, self.nomin_fiat_ask_qty)
        pre_nomins = self.nomins
        self.sell_fiat_for_nomins_with_fee(f_qty)
        n_qty = min(self.nomins - pre_nomins, self.havven_nomin_ask_qty)
        self.sell_nomins_for_havvens_with_fee(n_qty)

    def forward_fiat_cycle_balances(self) -> Dict[str, Dec]:
        """
        Return the estimated wallet balances of this agent after
        one forward fiat arbitrage cycle: fiat -> nomins -> havvens -> fiat.
        """
        havvens = self.havvens
        nomins = self.nomins
        fiat = self.fiat

        f_qty = min(fiat, self.nomin_fiat_ask_qty)
        fiat -= f_qty
        n_qty = self.fiat_to_nomin_yield(f_qty)
        nomins += n_qty
        n_qty = min(n_qty, self.havven_nomin_ask_qty)
        nomins -= n_qty
        c_qty = self.nomin_to_havven_yield(n_qty)
        havvens += c_qty
        c_qty = min(c_qty, self.havven_fiat_bid_qty)
        havvens -= c_qty
        f_qty = self.havven_to_fiat_yield(c_qty)
        fiat += f_qty

        return {"havvens": havvens, "nomins": nomins, "fiat": fiat}

    def forward_fiat_cycle_trade(self) -> None:
        """
        Perform a single forward fiat arbitrage cycle;
        fiat -> nomins -> havvens -> fiat.
        """
        f_qty = min(self.available_fiat, self.nomin_fiat_ask_qty)
        pre_nomins = self.nomins
        self.sell_fiat_for_nomins_with_fee(f_qty)
        n_qty = min(self.nomins - pre_nomins, self.havven_nomin_ask_qty)
        pre_havvens = self.havvens
        self.sell_nomins_for_havvens_with_fee(n_qty)
        c_qty = min(self.havvens - pre_havvens, self.havven_fiat_bid_qty)
        self.sell_havvens_for_fiat_with_fee(c_qty)

    def forward_nomin_cycle_balances(self) -> Dict[str, Dec]:
        """
        Return the estimated wallet balances of this agent after
        one forward nomin arbitrage cycle: nomins -> havvens -> fiat -> nomins.
        """
        havvens = self.havvens
        nomins = self.nomins
        fiat = self.fiat

        n_qty = min(nomins, self.havven_nomin_ask_qty)
        nomins -= n_qty
        c_qty = self.nomin_to_havven_yield(n_qty)
        havvens += c_qty
        c_qty = min(c_qty, self.havven_fiat_bid_qty)
        havvens -= c_qty
        f_qty = self.havven_to_fiat_yield(c_qty)
        fiat += f_qty
        f_qty = min(f_qty, self.nomin_fiat_ask_qty)
        fiat -= f_qty
        n_qty = self.fiat_to_nomin_yield(f_qty)
        nomins += n_qty

        return {"havvens": havvens, "nomins": nomins, "fiat": fiat}

    def forward_nomin_cycle_trade(self) -> None:
        """
        Perform a single forward nomin arbitrage cycle;
        nomins -> havvens -> fiat -> nomins.
        """
        n_qty = min(self.available_nomins, self.havven_nomin_ask_qty)
        pre_havvens = self.havvens
        self.sell_nomins_for_havvens_with_fee(n_qty)
        c_qty = min(self.havvens - pre_havvens, self.havven_fiat_bid_qty)
        pre_fiat = self.fiat
        self.sell_havvens_for_fiat_with_fee(c_qty)
        f_qty = min(self.fiat - pre_fiat, self.nomin_fiat_ask_qty)
        self.sell_fiat_for_nomins_with_fee(f_qty)

    def reverse_havven_cycle_balances(self) -> Dict[str, Dec]:
        """
        Return the estimated wallet balances of this agent after
        one reverse havven arbitrage cycle: havvens -> nomins -> fiat -> havvens.
        """
        havvens = self.havvens
        nomins = self.nomins
        fiat = self.fiat

        c_qty = min(havvens, self.havven_nomin_bid_qty)
        havvens -= c_qty
        n_qty = self.havven_to_nomin_yield(c_qty)
        nomins += n_qty
        n_qty = min(n_qty, self.nomin_fiat_bid_qty)
        nomins -= n_qty
        f_qty = self.nomin_to_fiat_yield(n_qty)
        fiat += f_qty
        f_qty = min(f_qty, self.havven_fiat_ask_qty)
        fiat -= f_qty
        c_qty = self.fiat_to_havven_yield(f_qty)
        havvens += c_qty

        return {"havvens": havvens, "nomins": nomins, "fiat": fiat}

    def reverse_havven_cycle_trade(self) -> None:
        """
        Perform a single reverse havven arbitrage cycle;
        havvens -> nomins -> fiat -> havvens.
        """
        c_qty = min(self.available_havvens, self.havven_nomin_bid_qty)
        pre_nomins = self.nomins
        self.sell_havvens_for_nomins_with_fee(c_qty)
        n_qty = min(self.nomins - pre_nomins, self.nomin_fiat_bid_qty)
        pre_fiat = self.fiat
        self.sell_nomins_for_fiat_with_fee(n_qty)
        f_qty = min(self.fiat - pre_fiat, self.havven_fiat_ask_qty)
        self.sell_fiat_for_havvens_with_fee(f_qty)

    def reverse_nomin_cycle_balances(self) -> Dict[str, Dec]:
        """
        Return the estimated wallet balances of this agent after
        one reverse nomin arbitrage cycle: nomins -> fiat -> havvens -> nomins.
        """
        havvens = self.havvens
        nomins = self.nomins
        fiat = self.fiat

        n_qty = min(nomins, self.nomin_fiat_bid_qty)
        nomins -= n_qty
        f_qty = self.nomin_to_fiat_yield(n_qty)
        fiat += f_qty
        f_qty = min(f_qty, self.havven_fiat_ask_qty)
        fiat -= f_qty
        c_qty = self.fiat_to_havven_yield(f_qty)
        havvens += c_qty
        c_qty = min(c_qty, self.havven_nomin_bid_qty)
        havvens -= c_qty
        n_qty = self.havven_to_nomin_yield(c_qty)
        nomins += n_qty

        return {"havvens": havvens, "nomins": nomins, "fiat": fiat}

    def reverse_nomin_cycle_trade(self) -> None:
        """
        Perform a single reverse nomin arbitrage cycle;
        nomins -> fiat -> havvens -> nomins.
        """
        n_qty = min(self.available_nomins, self.nomin_fiat_bid_qty)
        pre_fiat = self.fiat
        self.sell_nomins_for_fiat_with_fee(n_qty)
        f_qty = min(self.fiat - pre_fiat, self.havven_fiat_ask_qty)
        pre_havvens = self.havvens
        self.sell_fiat_for_havvens_with_fee(f_qty)
        c_qty = min(self.havvens - pre_havvens, self.havven_nomin_bid_qty)
        self.sell_havvens_for_nomins_with_fee(c_qty)

    def reverse_fiat_cycle_balances(self) -> Dict[str, Dec]:
        """
        Return the estimated wallet balances of this agent after
        one reverse fiat arbitrage cycle: fiat -> havvens -> nomins -> fiat.
        """
        havvens = self.havvens
        nomins = self.nomins
        fiat = self.fiat

        f_qty = min(fiat, self.havven_fiat_ask_qty)
        fiat -= f_qty
        c_qty = self.fiat_to_havven_yield(f_qty)
        havvens += c_qty
        c_qty = min(c_qty, self.havven_nomin_bid_qty)
        havvens -= c_qty
        n_qty = self.havven_to_nomin_yield(c_qty)
        nomins += n_qty
        n_qty = min(n_qty, self.nomin_fiat_bid_qty)
        nomins -= n_qty
        f_qty = self.nomin_to_fiat_yield(n_qty)
        fiat += f_qty

        return {"havvens": havvens, "nomins": nomins, "fiat": fiat}

    def reverse_fiat_cycle_trade(self) -> None:
        """
        Perform a single reverse fiat arbitrage cycle;
        fiat -> havvens -> nomins -> fiat.
        """
        f_qty = min(self.available_fiat, self.havven_fiat_ask_qty)
        pre_havvens = self.havvens
        self.sell_fiat_for_havvens_with_fee(f_qty)
        c_qty = min(self.havvens - pre_havvens, self.havven_nomin_bid_qty)
        self.sell_havvens_for_nomins_with_fee(c_qty)
        pre_nomins = self.nomins
        n_qty = min(self.nomins - pre_nomins, self.nomin_fiat_bid_qty)
        self.sell_nomins_for_fiat_with_fee(n_qty)

    def _cycle_fee_rate(self) -> Dec:
        """Divide by this fee rate to determine losses after one traversal of an arbitrage cycle."""
        return hm.round_decimal((Dec(1) + self.model.fee_manager.nomin_fee_rate) * \
                                (Dec(1) + self.model.fee_manager.havven_fee_rate) * \
                                (Dec(1) + self.model.fee_manager.fiat_fee_rate))

    def _forward_multiple_no_fees(self) -> Dec:
        """
        The value multiple after one forward arbitrage cycle, neglecting fees.
        """
        # hav -> fiat -> nom -> hav
        return hm.round_decimal(self.havven_fiat_market.highest_bid_price() / \
                                (self.nomin_fiat_market.lowest_ask_price() *
                                 self.havven_nomin_market.lowest_ask_price()))

    def _reverse_multiple_no_fees(self) -> Dec:
        """
        The value multiple after one reverse arbitrage cycle, neglecting fees.
        """
        # hav -> nom -> fiat -> hav
        return hm.round_decimal((self.havven_nomin_market.highest_bid_price() *
                                 self.nomin_fiat_market.highest_bid_price()) / \
                                self.havven_fiat_market.lowest_ask_price())

    def _forward_multiple(self) -> Dec:
        """The return after one forward arbitrage cycle."""
        # Note, this only works because the fees are purely multiplicative.
        return hm.round_decimal(self._forward_multiple_no_fees() / self._cycle_fee_rate())

    def _reverse_multiple(self) -> Dec:
        """The return after one reverse arbitrage cycle."""
        # As above. If the fees were not just levied as percentages this would need to be updated.
        return hm.round_decimal(self._reverse_multiple_no_fees() / self._cycle_fee_rate())

    def _equalise_tokens(self) -> None:
        pass