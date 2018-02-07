from decimal import Decimal as Dec
from typing import Tuple, Optional

from managers import HavvenManager
from core import orderbook as ob
from .marketplayer import MarketPlayer


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
    initial_order = None

    _nomin_sell_rate_threshold = Dec('1.03')
    """The rate above which the player will sell nomins"""

    _nomin_buy_rate_threshold = Dec('0.99')
    """The rate below which the player will buy nomins"""

    def setup(self, init_value: Dec):
        self.wage_parameter = init_value/Dec(100)

        self.fiat = init_value * Dec(2)

    def step(self) -> None:
        super().step()

        # get rid of havvens, as that isn't the point of this player
        if self.available_havvens:
            self.sell_havvens_for_nomins(self.available_havvens)

        if self.available_nomins > 0:
            trade = self._find_best_nom_fiat_trade()
            last_price = 0
            while trade is not None and self.available_nomins > 0:
                if last_price == trade[0]:
                    break
                last_price = trade[0]
                ask = self._make_nom_fiat_trade(trade)
                trade = self._find_best_nom_fiat_trade()

        if self.available_fiat > 0:
            trade = self._find_best_fiat_nom_trade()
            last_price = 0
            while trade is not None and self.available_fiat > 0:
                # rarely, the entire order doesn't get filled, still trying to debug...
                if last_price == trade[0]:
                    break
                last_price = trade[0]
                bid = self._make_fiat_nom_trade(trade)
                trade = self._find_best_fiat_nom_trade()

    def _find_best_nom_fiat_trade(self) -> Optional[Tuple[Dec, Dec]]:
        trade_price_quant = None
        for bid in self.nomin_fiat_market.highest_bids():
            if bid.price < self._nomin_sell_rate_threshold:
                break
            if trade_price_quant is not None:
                trade_price_quant = (bid.price, trade_price_quant[1] + bid.quantity)
            else:
                trade_price_quant = (bid.price, bid.quantity)
        return trade_price_quant

    def _make_nom_fiat_trade(self, trade_price_quant: Tuple[Dec, Dec]) -> "ob.Ask":
        fee = self.model.fee_manager.transferred_nomins_fee(trade_price_quant[1])
        # if not enough nomins to cover whole ask
        if self.available_nomins < trade_price_quant[1] + fee:
            return self.sell_nomins_for_fiat_with_fee(self.available_nomins)
        return self.place_nomin_fiat_ask(trade_price_quant[1], trade_price_quant[0])

    def _find_best_fiat_nom_trade(self) -> Optional[Tuple[Dec, Dec]]:
        trade_price_quant = None
        for ask in self.nomin_fiat_market.lowest_asks():
            if ask.price > self._nomin_buy_rate_threshold:
                break
            if trade_price_quant is not None:
                trade_price_quant = (ask.price, trade_price_quant[1] + ask.quantity)
            else:
                trade_price_quant = (ask.price, ask.quantity)
        return trade_price_quant

    def _make_fiat_nom_trade(self, trade_price_quant: Tuple[Dec, Dec]) -> "ob.Bid":
        fee = self.model.fee_manager.transferred_fiat_fee(trade_price_quant[1])
        # if not enough fiat to cover whole bid
        if self.available_fiat < trade_price_quant[1] + fee:
            return self.sell_fiat_for_nomins_with_fee(self.available_fiat)
        return self.place_nomin_fiat_bid(trade_price_quant[1], trade_price_quant[0])


class HavvenEscrowNominShorter(NominShorter):
    """
    Escrows havvens for nomins when the rate of nom->fiat is favourable
    then waits for market to stabilise, trusting that nomin price will go back
    to 1

    havvens-(issue)->nomins->fiat(and wait)->nomin-(burn)->havvens+extra nomins

    This should profit on the issuing and burning mechanics (if they scale
    with the price), the nomin/fiat trade and accruing fees

    In the end this player should hold escrowed havvens and nomins left over that he
    can't burn
    """

    def setup(self, init_value: Dec):
        self.wage_parameter = init_value/Dec(100)

        self.havvens = init_value * Dec(2)
        self.fiat = init_value

    def step(self) -> None:
        pass
        # # TODO: rewrite logic
        #     # keep all havvens escrowed to make issuing nomins easier
        #     if self.available_havvens > 0:
        #         self.escrow_havvens(self.available_havvens)
        #
        #     nomins = self.available_nomins + self.remaining_issuance_rights()
        #
        #     if nomins > 0:
        #         trade = self._find_best_nom_fiat_trade()
        #         last_price = 0
        #         while trade is not None and HavvenManager.round_decimal(nomins) > 0:
        #             if last_price == trade[0]:
        #                 break
        #             last_price = trade[0]
        #             self._issue_nomins_up_to(trade[1])
        #             ask = self._make_nom_fiat_trade(trade)
        #             trade = self._find_best_nom_fiat_trade()
        #             nomins = self.available_nomins + self.remaining_issuance_rights()
        #
        #     if self.available_fiat > 0:
        #         trade = self._find_best_fiat_nom_trade()
        #         last_price = 0
        #         while trade is not None and HavvenManager.round_decimal(self.available_fiat) > 0:
        #             if last_price == trade[0]:
        #                 break
        #             last_price = trade[0]
        #             bid = self._make_fiat_nom_trade(trade)
        #             trade = self._find_best_fiat_nom_trade()
        #
        #     if self.issued_nomins:
        #         if self.available_nomins < self.issued_nomins:
        #             self.burn_nomins(self.available_nomins)
        #         else:
        #             self.burn_nomins(self.issued_nomins)
        #
        # def _issue_nomins_up_to(self, quantity: Dec) -> bool:
        #     """
        #     If quantity > currently issued nomins, including fees to trade, issue more nomins
        #
        #     If the player cant issue more nomins than the quantity,
        #     """
        #     fee = HavvenManager.round_decimal(self.model.fee_manager.transferred_nomins_fee(quantity))
        #
        #     # if there are enough nomins, return
        #     if self.available_nomins > fee + quantity:
        #         return True
        #
        #     nomins_needed = fee + quantity - self.available_nomins
        #
        #     if self.remaining_issuance_rights() > nomins_needed:
        #         return self.issue_nomins(nomins_needed)
        #     else:
        #         return self.issue_nomins(self.remaining_issuance_rights())
