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
    """
    nom_sell = None
    nom_buy = None

    _nomin_sell_rate_minimum = Dec('1.01')
    """The rate above which the player will sell nomins"""

    _nomin_buy_rate_maximum = Dec('0.99')
    """The rate below which the player will buy nomins"""

    _nomin_buy_wait = 0
    _nomin_sell_wait = 0

    def setup(self, wealth_parameter: Dec, wage_parameter: Dec, liquidation_param: Dec) -> None:
        super().setup(wealth_parameter, wage_parameter, liquidation_param)

        self.fiat = wealth_parameter * Dec(3)

    def step(self) -> None:
        super().step()
        if self.nom_buy:
            self.nom_buy.cancel()
        if self.nom_sell:
            self.nom_sell.cancel()

        # get rid of havvens, as that isn't the point of this player
        if self.available_havvens:
            self.sell_havvens_for_nomins_with_fee(self.available_havvens)
            self.sell_havvens_for_fiat_with_fee(self.available_havvens)

        if self.available_nomins > 0:
            price = self._nomin_sell_rate_minimum + self.patience_function(self._nomin_sell_wait)
            self.nom_sell = self.place_nomin_fiat_ask_with_fee(self.available_nomins, price)

        if self.available_fiat > 0:
            price = self._nomin_buy_rate_maximum - self.patience_function(self._nomin_buy_wait)
            self.nom_buy = self.place_nomin_fiat_bid_with_fee(self.available_fiat, price)

    @staticmethod
    def patience_function(wait) -> Dec:
        return Dec(min((0.5/(wait+10)), 0.0))

    def notify_trade(self, record: "ob.TradeRecord"):
        if record.buyer == self:
            self._nomin_buy_wait = 0
        if record.seller == self:
            self._nomin_sell_wait = 0


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

    def setup(self, wealth_parameter: Dec, wage_parameter: Dec, liquidation_param: Dec) -> None:
        super().setup(wealth_parameter, wage_parameter, liquidation_param)

        self.havvens = wealth_parameter * Dec(2)
        self.fiat = wealth_parameter

    def step(self) -> None:
        if self.nom_buy:
            self.nom_buy.cancel()
        if self.nom_sell:
            self.nom_sell.cancel()

        if self.nomin_fiat_market.highest_bid_price() > (
                self._nomin_sell_rate_minimum + self.patience_function(self._nomin_sell_wait)
        ):
            quant = self.nomin_fiat_market.highest_bid_quantity()
            self.issue_nomins(quant)  # this isn't instant, issuance controller waits to next step

        if self.nomin_fiat_market.lowest_ask_price() < (
                self._nomin_buy_rate_maximum - self.patience_function(self._nomin_buy_wait)
        ):
            quant = self.nomin_fiat_market.lowest_ask_quantity()
            self.sell_fiat_for_nomins_with_fee(min(quant, self.available_nomins))
            self.burn_nomins(self.available_nomins)
