from .marketplayer import MarketPlayer

class Arbitrageur(MarketPlayer):
    """Wants to find arbitrage cycles and exploit them to equalise prices."""

    def step(self) -> None:
        """Find an exploitable arbitrage cycle."""
        # The only cycles that exist are CUR -> FIAT -> NOM -> CUR,
        # its rotations, and the reverse cycles.
        # The bot will act to place orders in all markets at once,
        # if there is an arbitrage opportunity, taking into account
        # the fee rates.

        if self._forward_multiple_() > 1.1:
            # Trade in the forward direction
            # TODO: work out which rotation of this cycle would be the least wasteful
            # cur -> fiat -> nom -> cur
            fn_price = 1.0 / self.model.trade_manager.nom_fiat_market.lowest_ask_price()
            nc_price = 1.0 / self.model.trade_manager.cur_nom_market.lowest_ask_price()

            cf_qty = sum(b.quantity for b in self.model.trade_manager.cur_fiat_market.highest_bids())
            fn_qty = sum(a.quantity for a in self.model.trade_manager.nom_fiat_market.lowest_asks())
            nc_qty = sum(a.quantity for a in self.model.trade_manager.cur_nom_market.lowest_asks())

            c_qty = min(self.curits, cf_qty)
            self.sell_curits_for_fiat(c_qty)

            f_qty = min(self.fiat, fn_qty * fn_price)
            self.sell_fiat_for_curits(f_qty)

            n_qty = min(self.nomins, nc_qty * nc_price)
            self.sell_nomins_for_curits(n_qty)

        elif self._reverse_multiple_() > 1.1:
            # Trade in the reverse direction
            # cur -> nom -> fiat -> cur
            fc_price = 1.0 / self.model.trade_manager.cur_fiat_market.lowest_ask_price()

            cn_qty = sum(b.quantity for b in self.model.trade_manager.cur_nom_market.highest_bids())
            nf_qty = sum(b.quantity for b in self.model.trade_manager.nom_fiat_market.highest_bids())
            fc_qty = sum(a.quantity for a in self.model.trade_manager.cur_fiat_market.lowest_asks())

            c_qty = min(self.curits, cn_qty)
            self.sell_curits_for_nomins(c_qty)

            n_qty = min(self.nomins, nf_qty)
            self.sell_nomins_for_fiat(n_qty)

            f_qty = min(self.fiat, fc_qty * fc_price)
            self.sell_nomins_for_curits(n_qty)

    def _cycle_fee_rate_(self) -> float:
        """Divide by this fee rate to determine losses after one traversal of an arbitrage cycle."""
        return (1 + self.model.fee_manager.transfer_nomins_fee(1)) * \
               (1 + self.model.fee_manager.transfer_curits_fee(1)) * \
               (1 + self.model.fee_manager.transfer_fiat_fee(1))

    def _forward_multiple_no_fees_(self) -> float:
        """
        The value multiple after one forward arbitrage cycle, neglecting fees.
        """
        # cur -> fiat -> nom -> cur
        return self.model.trade_manager.cur_fiat_market.highest_bid_price() / \
            self.model.trade_manager.nom_fiat_market.lowest_ask_price() * \
            self.model.trade_manager.cur_nom_market.lowest_ask_price()

    def _reverse_multiple_no_fees_(self) -> float:
        """
        The value multiple after one reverse arbitrage cycle, neglecting fees.
        """
        # cur -> nom -> fiat -> cur
        return self.model.trade_manager.cur_nom_market.highest_bid_price() * \
            self.model.trade_manager.nom_fiat_market.highest_bid_price() / \
            self.model.trade_manager.cur_fiat_market.lowest_ask_price()

    def _forward_multiple_(self) -> float:
        """The return after one forward arbitrage cycle."""
        # Note, this only works because the fees are purely multiplicative.
        return self._forward_multiple_no_fees_() / self._cycle_fee_rate_()

    def _reverse_multiple_(self) -> float:
        """The return after one reverse arbitrage cycle."""
        # As above. If the fees were not just levied as percentages this would need to be updated.
        return self._reverse_multiple_no_fees_() / self._cycle_fee_rate_()

    def _equalise_tokens_(self) -> None:
        pass
