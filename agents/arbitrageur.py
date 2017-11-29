from typing import Dict
from decimal import Decimal as Dec

from .marketplayer import MarketPlayer

from managers import HavvenManager as hm
from orderbook import OrderBook


class Arbitrageur(MarketPlayer):
    """Wants to find arbitrage cycles and exploit them to equalise prices."""
    def __init__(self, unique_id: int, havven: "model.Havven",
                 fiat: Dec = Dec(0), curits: Dec = Dec(0),
                 nomins: Dec = Dec(0),
                 profit_threshold: Dec = Dec('0.05')) -> None:

        super().__init__(unique_id, havven, fiat=fiat,
                         curits=curits, nomins=nomins)

        self.profit_threshold = profit_threshold
        """
        This arbitrageur will only trade if it can make a profit higher than
        this fraction.
        """

        # Cached values of the amount available in arb cycles for performance
        # and neatness.
        self.curit_fiat_bid_qty = Dec(0)
        self.curit_nomin_bid_qty = Dec(0)
        self.nomin_fiat_bid_qty = Dec(0)
        self.nomin_fiat_ask_qty = Dec(0)
        self.curit_nomin_ask_qty = Dec(0)
        self.curit_fiat_ask_qty = Dec(0)

    def step(self) -> None:
        """
        Find an exploitable arbitrage cycle.

        The only cycles that exist are CUR -> FIAT -> NOM -> CUR,
        its rotations, and the reverse cycles.
        This bot will consider those and act to exploit the most
        favourable such cycle if the profit available around that
        cycle is better than the profit threshold (including fees).
        """

        self.curit_fiat_bid_qty = self.curit_fiat_market.highest_bid_quantity()
        self.curit_nomin_bid_qty = self.curit_nomin_market.highest_bid_quantity()
        self.nomin_fiat_bid_qty = self.nomin_fiat_market.highest_bid_quantity()
        self.nomin_fiat_ask_qty = hm.round_decimal(self.nomin_fiat_market.lowest_ask_quantity()
                                                   * self.nomin_fiat_market.lowest_ask_price())
        self.curit_nomin_ask_qty = hm.round_decimal(self.curit_nomin_market.lowest_ask_quantity()
                                                    * self.curit_nomin_market.lowest_ask_price())
        self.curit_fiat_ask_qty = hm.round_decimal(self.curit_fiat_market.lowest_ask_quantity()
                                                   * self.curit_fiat_market.lowest_ask_price())

        wealth = self.wealth()

        # Consider the forward direction
        cc_net_wealth = self.model.fiat_value(**self.forward_curit_cycle_balances()) - wealth
        nn_net_wealth = self.model.fiat_value(**self.forward_nomin_cycle_balances()) - wealth
        ff_net_wealth = self.model.fiat_value(**self.forward_fiat_cycle_balances()) - wealth
        max_net_wealth = max(cc_net_wealth, nn_net_wealth, ff_net_wealth)

        if max_net_wealth > self.profit_threshold:
            if cc_net_wealth == max_net_wealth:
                self.forward_curit_cycle_trade()
            elif nn_net_wealth == max_net_wealth:
                self.forward_nomin_cycle_trade()
            else:
                self.forward_fiat_cycle_trade()

        # Now the reverse direction
        cc_net_wealth = self.model.fiat_value(**self.reverse_curit_cycle_balances()) - wealth
        nn_net_wealth = self.model.fiat_value(**self.reverse_nomin_cycle_balances()) - wealth
        ff_net_wealth = self.model.fiat_value(**self.reverse_fiat_cycle_balances()) - wealth
        max_net_wealth = max(cc_net_wealth, nn_net_wealth, ff_net_wealth)

        if max_net_wealth > self.profit_threshold:
            if cc_net_wealth == max_net_wealth:
                self.reverse_curit_cycle_trade()
            elif nn_net_wealth == max_net_wealth:
                self.reverse_nomin_cycle_trade()
            else:
                self.reverse_fiat_cycle_trade()

    @staticmethod
    def _base_to_quoted_yield_(market: OrderBook, base_capital: Dec) -> Dec:
        """
        The quantity of the quoted currency you could obtain at the current
        best market price, selling a given quantity of the base currency.
        """
        price = market.highest_bid_price()
        feeless_capital = market._ask_qty_received_fn_(base_capital)
        return market.bids_not_lower_quoted_quantity(price, feeless_capital)

    @staticmethod
    def _quoted_to_base_yield(market: OrderBook, quoted_capital: Dec) -> Dec:
        """
        The quantity of the base currency you could obtain at the current
        best market price, selling a given quantity of the quoted currency.
        """
        price = market.lowest_ask_price()
        feeless_capital = market._bid_qty_received_fn_(quoted_capital)
        return market.asks_not_higher_base_quantity(price, feeless_capital)

    def curit_to_fiat_yield(self, capital: Dec) -> Dec:
        """
        The quantity of fiat obtained, spending a quantity of curits.
        """
        return self._base_to_quoted_yield_(self.curit_fiat_market, capital)

    def fiat_to_curit_yield(self, capital: Dec) -> Dec:
        """
        The quantity of curits obtained, spending a quantity of fiat.
        """
        return self._quoted_to_base_yield(self.curit_fiat_market, capital)

    def curit_to_nomin_yield(self, capital: Dec) -> Dec:
        """
        The quantity of nomins obtained, spending a quantity of curits.
        """
        return self._base_to_quoted_yield_(self.curit_nomin_market, capital)

    def nomin_to_curit_yield(self, capital: Dec) -> Dec:
        """
        The quantity of curits obtained, spending a quantity of nomins.
        """
        return self._quoted_to_base_yield(self.curit_nomin_market, capital)

    def nomin_to_fiat_yield(self, capital: Dec) -> Dec:
        """
        The quantity of fiat obtained, spending a quantity of nomins.
        """
        return self._base_to_quoted_yield_(self.nomin_fiat_market, capital)

    def fiat_to_nomin_yield(self, capital: Dec) -> Dec:
        """
        The quantity of nomins obtained, spending a quantity of fiat.
        """
        return self._quoted_to_base_yield(self.nomin_fiat_market, capital)

    def forward_curit_cycle_balances(self) -> Dict[str, Dec]:
        """
        Return the estimated wallet balances of this agent after
        one forward curit arbitrage cycle: curits -> fiat -> nomins -> curits.
        """
        curits = self.curits
        nomins = self.nomins
        fiat = self.fiat

        c_qty = min(curits, self.curit_fiat_bid_qty)
        curits -= c_qty
        f_qty = self.curit_to_fiat_yield(c_qty)
        fiat += f_qty
        f_qty = min(f_qty, self.nomin_fiat_ask_qty)
        fiat -= f_qty
        n_qty = self.fiat_to_nomin_yield(f_qty)
        nomins += n_qty
        n_qty = min(n_qty, self.curit_nomin_ask_qty)
        nomins -= n_qty
        c_qty = self.nomin_to_curit_yield(n_qty)
        curits += c_qty

        return {"curits": curits, "nomins": nomins, "fiat": fiat}

    def forward_curit_cycle_trade(self) -> None:
        """
        Perform a single forward curit arbitrage cycle;
        curits -> fiat -> nomins -> curits.
        """
        c_qty = min(self.available_curits, self.curit_fiat_bid_qty)
        pre_fiat = self.fiat
        self.sell_curits_for_fiat_with_fee(c_qty)
        f_qty = min(self.fiat - pre_fiat, self.nomin_fiat_ask_qty)
        pre_nomins = self.nomins
        self.sell_fiat_for_nomins_with_fee(f_qty)
        n_qty = min(self.nomins - pre_nomins, self.curit_nomin_ask_qty)
        self.sell_nomins_for_curits_with_fee(n_qty)

    def forward_fiat_cycle_balances(self) -> Dict[str, Dec]:
        """
        Return the estimated wallet balances of this agent after
        one forward fiat arbitrage cycle: fiat -> nomins -> curits -> fiat.
        """
        curits = self.curits
        nomins = self.nomins
        fiat = self.fiat

        f_qty = min(fiat, self.nomin_fiat_ask_qty)
        fiat -= f_qty
        n_qty = self.fiat_to_nomin_yield(f_qty)
        nomins += n_qty
        n_qty = min(n_qty, self.curit_nomin_ask_qty)
        nomins -= n_qty
        c_qty = self.nomin_to_curit_yield(n_qty)
        curits += c_qty
        c_qty = min(c_qty, self.curit_fiat_bid_qty)
        curits -= c_qty
        f_qty = self.curit_to_fiat_yield(c_qty)
        fiat += f_qty

        return {"curits": curits, "nomins": nomins, "fiat": fiat}

    def forward_fiat_cycle_trade(self) -> None:
        """
        Perform a single forward fiat arbitrage cycle;
        fiat -> nomins -> curits -> fiat.
        """
        f_qty = min(self.available_fiat, self.nomin_fiat_ask_qty)
        pre_nomins = self.nomins
        self.sell_fiat_for_nomins_with_fee(f_qty)
        n_qty = min(self.nomins - pre_nomins, self.curit_nomin_ask_qty)
        pre_curits = self.curits
        self.sell_nomins_for_curits_with_fee(n_qty)
        c_qty = min(self.curits - pre_curits, self.curit_fiat_bid_qty)
        self.sell_curits_for_fiat_with_fee(c_qty)

    def forward_nomin_cycle_balances(self) -> Dict[str, Dec]:
        """
        Return the estimated wallet balances of this agent after
        one forward nomin arbitrage cycle: nomins -> curits -> fiat -> nomins.
        """
        curits = self.curits
        nomins = self.nomins
        fiat = self.fiat

        n_qty = min(nomins, self.curit_nomin_ask_qty)
        nomins -= n_qty
        c_qty = self.nomin_to_curit_yield(n_qty)
        curits += c_qty
        c_qty = min(c_qty, self.curit_fiat_bid_qty)
        curits -= c_qty
        f_qty = self.curit_to_fiat_yield(c_qty)
        fiat += f_qty
        f_qty = min(f_qty, self.nomin_fiat_ask_qty)
        fiat -= f_qty
        n_qty = self.fiat_to_nomin_yield(f_qty)
        nomins += n_qty

        return {"curits": curits, "nomins": nomins, "fiat": fiat}

    def forward_nomin_cycle_trade(self) -> None:
        """
        Perform a single forward nomin arbitrage cycle;
        nomins -> curits -> fiat -> nomins.
        """
        n_qty = min(self.available_nomins, self.curit_nomin_ask_qty)
        pre_curits = self.curits
        self.sell_nomins_for_curits_with_fee(n_qty)
        c_qty = min(self.curits - pre_curits, self.curit_fiat_bid_qty)
        pre_fiat = self.fiat
        self.sell_curits_for_fiat_with_fee(c_qty)
        f_qty = min(self.fiat - pre_fiat, self.nomin_fiat_ask_qty)
        self.sell_fiat_for_nomins_with_fee(f_qty)

    def reverse_curit_cycle_balances(self) -> Dict[str, Dec]:
        """
        Return the estimated wallet balances of this agent after
        one reverse curit arbitrage cycle: curits -> nomins -> fiat -> curits.
        """
        curits = self.curits
        nomins = self.nomins
        fiat = self.fiat

        c_qty = min(curits, self.curit_nomin_bid_qty)
        curits -= c_qty
        n_qty = self.curit_to_nomin_yield(c_qty)
        nomins += n_qty
        n_qty = min(n_qty, self.nomin_fiat_bid_qty)
        nomins -= n_qty
        f_qty = self.nomin_to_fiat_yield(n_qty)
        fiat += f_qty
        f_qty = min(f_qty, self.curit_fiat_ask_qty)
        fiat -= f_qty
        c_qty = self.fiat_to_curit_yield(f_qty)
        curits += c_qty

        return {"curits": curits, "nomins": nomins, "fiat": fiat}

    def reverse_curit_cycle_trade(self) -> None:
        """
        Perform a single reverse curit arbitrage cycle;
        curits -> nomins -> fiat -> curits.
        """
        c_qty = min(self.available_curits, self.curit_nomin_bid_qty)
        pre_nomins = self.nomins
        self.sell_curits_for_nomins_with_fee(c_qty)
        n_qty = min(self.nomins - pre_nomins, self.nomin_fiat_bid_qty)
        pre_fiat = self.fiat
        self.sell_nomins_for_fiat_with_fee(n_qty)
        f_qty = min(self.fiat - pre_fiat, self.curit_fiat_ask_qty)
        self.sell_fiat_for_curits_with_fee(f_qty)

    def reverse_nomin_cycle_balances(self) -> Dict[str, Dec]:
        """
        Return the estimated wallet balances of this agent after
        one reverse nomin arbitrage cycle: nomins -> fiat -> curits -> nomins.
        """
        curits = self.curits
        nomins = self.nomins
        fiat = self.fiat

        n_qty = min(nomins, self.nomin_fiat_bid_qty)
        nomins -= n_qty
        f_qty = self.nomin_to_fiat_yield(n_qty)
        fiat += f_qty
        f_qty = min(f_qty, self.curit_fiat_ask_qty)
        fiat -= f_qty
        c_qty = self.fiat_to_curit_yield(f_qty)
        curits += c_qty
        c_qty = min(c_qty, self.curit_nomin_bid_qty)
        curits -= c_qty
        n_qty = self.curit_to_nomin_yield(c_qty)
        nomins += n_qty

        return {"curits": curits, "nomins": nomins, "fiat": fiat}

    def reverse_nomin_cycle_trade(self) -> None:
        """
        Perform a single reverse nomin arbitrage cycle;
        nomins -> fiat -> curits -> nomins.
        """
        n_qty = min(self.available_nomins, self.nomin_fiat_bid_qty)
        pre_fiat = self.fiat
        self.sell_nomins_for_fiat_with_fee(n_qty)
        f_qty = min(self.fiat - pre_fiat, self.curit_fiat_ask_qty)
        pre_curits = self.curits
        self.sell_fiat_for_curits_with_fee(f_qty)
        c_qty = min(self.curits - pre_curits, self.curit_nomin_bid_qty)
        self.sell_curits_for_nomins_with_fee(c_qty)

    def reverse_fiat_cycle_balances(self) -> Dict[str, Dec]:
        """
        Return the estimated wallet balances of this agent after
        one reverse fiat arbitrage cycle: fiat -> curits -> nomins -> fiat.
        """
        curits = self.curits
        nomins = self.nomins
        fiat = self.fiat

        f_qty = min(fiat, self.curit_fiat_ask_qty)
        fiat -= f_qty
        c_qty = self.fiat_to_curit_yield(f_qty)
        curits += c_qty
        c_qty = min(c_qty, self.curit_nomin_bid_qty)
        curits -= c_qty
        n_qty = self.curit_to_nomin_yield(c_qty)
        nomins += n_qty
        n_qty = min(n_qty, self.nomin_fiat_bid_qty)
        nomins -= n_qty
        f_qty = self.nomin_to_fiat_yield(n_qty)
        fiat += f_qty

        return {"curits": curits, "nomins": nomins, "fiat": fiat}

    def reverse_fiat_cycle_trade(self) -> None:
        """
        Perform a single reverse fiat arbitrage cycle;
        fiat -> curits -> nomins -> fiat.
        """
        f_qty = min(self.available_fiat, self.curit_fiat_ask_qty)
        pre_curits = self.curits
        self.sell_fiat_for_curits_with_fee(f_qty)
        c_qty = min(self.curits - pre_curits, self.curit_nomin_bid_qty)
        self.sell_curits_for_nomins_with_fee(c_qty)
        pre_nomins = self.nomins
        n_qty = min(self.nomins - pre_nomins, self.nomin_fiat_bid_qty)
        self.sell_nomins_for_fiat_with_fee(n_qty)

    def _cycle_fee_rate_(self) -> Dec:
        """Divide by this fee rate to determine losses after one traversal of an arbitrage cycle."""
        return hm.round_decimal((Dec(1) + self.model.fee_manager.nom_fee_rate) * \
                                (Dec(1) + self.model.fee_manager.cur_fee_rate) * \
                                (Dec(1) + self.model.fee_manager.fiat_fee_rate))

    def _forward_multiple_no_fees_(self) -> Dec:
        """
        The value multiple after one forward arbitrage cycle, neglecting fees.
        """
        # cur -> fiat -> nom -> cur
        return hm.round_decimal(self.curit_fiat_market.highest_bid_price() / \
                                (self.nomin_fiat_market.lowest_ask_price() *
                                 self.curit_nomin_market.lowest_ask_price()))

    def _reverse_multiple_no_fees_(self) -> Dec:
        """
        The value multiple after one reverse arbitrage cycle, neglecting fees.
        """
        # cur -> nom -> fiat -> cur
        return hm.round_decimal((self.curit_nomin_market.highest_bid_price() *
                                 self.nomin_fiat_market.highest_bid_price()) / \
                                self.curit_fiat_market.lowest_ask_price())

    def _forward_multiple_(self) -> Dec:
        """The return after one forward arbitrage cycle."""
        # Note, this only works because the fees are purely multiplicative.
        return hm.round_decimal(self._forward_multiple_no_fees_() / self._cycle_fee_rate_())

    def _reverse_multiple_(self) -> Dec:
        """The return after one reverse arbitrage cycle."""
        # As above. If the fees were not just levied as percentages this would need to be updated.
        return hm.round_decimal(self._reverse_multiple_no_fees_() / self._cycle_fee_rate_())

    def _equalise_tokens_(self) -> None:
        pass