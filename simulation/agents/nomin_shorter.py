from typing import Tuple, Optional
from decimal import Decimal

from .marketplayer import MarketPlayer
import orderbook as ob
from managers import HavvenManager


class NominShorter(MarketPlayer):
    """
    Holds onto nomins until the nomin->fiat price is favourable
      Then trades nomins for fiat and holds until the nomin price stabilises
      Then trades fiat for nomins

    Primary aim is to increase amount of nomins

    TODO: Rates should be set based on fees (should try to make at least 0.5% or so on each cycle),
      Also rates could be set based on some random factor per player that can dictate
      the upper limit, lower limit and gap between limits


    TODO: Maybe put up a wall by placing nomin ask @ sell_rate_threshold
    """

    _nomin_sell_rate_threshold = Decimal('1.04')
    """The rate above which the player will sell nomins"""

    _nomin_buy_rate_threshold = Decimal('1.01')
    """The rate below which the player will buy nomins"""

    def step(self) -> None:
        # get rid of curits, as that isn't the point of this player
        if self.curits:
            self.sell_curits_for_nomins(self.curits)

        if self.nomins > 0:
            trade = self._find_best_nom_fiat_trade()
            count = 10  # to avoid long loops of smaller and smaller trades
            while count > 0 and trade is not None and self.nomins > 0:
                count -= 1
                ask = self._make_nom_fiat_trade(trade)
                trade = self._find_best_nom_fiat_trade()

        if self.fiat > 0:
            trade = self._find_best_fiat_nom_trade()
            count = 10  # to avoid long loops of smaller and smaller trades
            while count > 0 and trade is not None and self.fiat > 0:
                count -= 1
                bid = self._make_fiat_nom_trade(trade)
                trade = self._find_best_fiat_nom_trade()

    def _find_best_nom_fiat_trade(self) -> Optional[Tuple["Decimal", "Decimal"]]:
        trade_price_quant = None
        for bid in self.model.market_manager.nomin_fiat_market.highest_bids():
            if bid.price < self._nomin_sell_rate_threshold:
                break
            if trade_price_quant is not None:
                trade_price_quant = (bid.price, trade_price_quant[1] + bid.quantity)
            else:
                trade_price_quant = (bid.price, bid.quantity)
        return trade_price_quant

    def _make_nom_fiat_trade(self, trade_price_quant: Tuple["Decimal", "Decimal"]) -> "ob.Ask":
        fee = self.model.fee_manager.transferred_nomins_fee(trade_price_quant[1])
        # if not enough nomins to cover whole ask
        if self.nomins < trade_price_quant[1] + fee:
            return self.sell_nomins_for_fiat_with_fee(self.nomins)
        return self.sell_nomins_for_fiat(trade_price_quant[1])

    def _find_best_fiat_nom_trade(self) -> Optional[Tuple["Decimal", "Decimal"]]:
        trade_price_quant = None
        for ask in self.model.market_manager.nomin_fiat_market.lowest_asks():
            if ask.price > self._nomin_buy_rate_threshold:
                break
            if trade_price_quant is not None:
                trade_price_quant = (ask.price, trade_price_quant[1] + ask.quantity)
            else:
                trade_price_quant = (ask.price, ask.quantity)
        return trade_price_quant

    def _make_fiat_nom_trade(self, trade_price_quant: Tuple["Decimal", "Decimal"]) -> "ob.Bid":
        fee = self.model.fee_manager.transferred_fiat_fee(trade_price_quant[1])
        # if not enough fiat to cover whole ask
        if self.fiat < trade_price_quant[1] + fee:
            return self.sell_fiat_for_nomins_with_fee(self.fiat)
        return self.sell_fiat_for_nomins(trade_price_quant[1])


class CuritEscrowNominShorter(NominShorter):
    """
    Escrows curits for nomins when the rate of nom->fiat is favourable
    then waits for market to stabilise, trusting that nomin price will go back
    to 1

    curits-(issue)->nomins->fiat(and wait)->nomin-(burn)->curits+extra nomins

    This should profit on the issuing and burning mechanics (if they scale
    with the price), the nomin/fiat trade and accruing fees

    In the end this player should hold escrowed curits and nomins left over that he
    can't burn
    """
    def step(self) -> None:
        # keep all curits escrowed to make issuing nomins easier
        if self.curits > 0:
            self.escrow_curits(self.curits)

        nomins = self.nomins + self.remaining_issuance_rights()

        if nomins > 0:
            count = 10  # to avoid long loops of smaller and smaller trades
            trade = self._find_best_nom_fiat_trade()
            while count > 0 and trade is not None and HavvenManager.round_decimal(nomins) > 0:
                count -= 1
                self._issue_nomins_up_to(trade[1])
                ask = self._make_nom_fiat_trade(trade)
                trade = self._find_best_nom_fiat_trade()
                nomins = self.nomins + self.remaining_issuance_rights()

        if self.fiat > 0:
            count = 10  # to avoid long loops of smaller and smaller trades
            trade = self._find_best_fiat_nom_trade()
            while count > 0 and trade is not None and HavvenManager.round_decimal(self.fiat) > 0:
                count -= 1
                bid = self._make_fiat_nom_trade(trade)
                trade = self._find_best_fiat_nom_trade()

        if self.issued_nomins:
            if self.nomins < self.issued_nomins:
                self.burn_nomins(self.nomins)
            else:
                self.burn_nomins(self.issued_nomins)

    def _issue_nomins_up_to(self, quantity: "Decimal") -> bool:
        """
        If quantity > currently issued nomins, including fees to trade, issue more nomins

        If the player cant issue more nomins than the quantity,
        """
        fee = HavvenManager.round_decimal(self.model.fee_manager.transferred_nomins_fee(quantity))

        # if there are enough nomins, return
        if self.nomins > fee + quantity:
            return True

        nomins_needed = fee + quantity - self.nomins

        if self.remaining_issuance_rights() > nomins_needed:
            return self.issue_nomins(nomins_needed)
        else:
            return self.issue_nomins(self.remaining_issuance_rights())
