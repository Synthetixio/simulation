from typing import Optional
from decimal import Decimal as Dec

from .marketplayer import MarketPlayer

import model
from managers import HavvenManager as hm


class CentralBank(MarketPlayer):
    """Attempts to use its cash reserves to stabilise prices at a certain level."""

    def __init__(self, unique_id: int, havven_model: "model.HavvenModel",
                 fiat: Dec = Dec(0), havvens: Dec = Dec(0),
                 nomins: Dec = Dec(0),
                 havven_target: Optional[Dec] = None,
                 nomin_target: Optional[Dec] = None,
                 havven_nomin_target: Optional[Dec] = None,
                 tolerance: Dec = Dec('0.01')) -> None:

        super().__init__(unique_id, havven_model, fiat=fiat,
                         havvens=havvens, nomins=nomins)

        # Note: it only really makes sense to target one of these at a time.
        # And operating on the assumption that arbitrage is working in the market.

        self.havven_target = havven_target
        """The targeted havven/fiat price."""

        self.nomin_target = nomin_target
        """The targeted nomin/fiat price."""

        # TODO: Actually use this
        self.havven_nomin_target = havven_nomin_target
        """The targeted havven/nomin exchange rate."""

        self.tolerance = tolerance
        """The bank will try to correct the price if it strays out of this range."""

    def step(self) -> None:

        self.cancel_orders()

        if self.havven_target is not None:
            havven_price = self.havven_fiat_market.price
            # Price is too high, it should decrease: we will sell havvens at a discount.
            if havven_price > hm.round_decimal(self.havven_target * (Dec(1) + self.tolerance)):
                # If we have havvens, sell them.
                if self.havvens > 0:
                    self.place_havven_fiat_ask_with_fee(self._fraction_(self.havvens),
                                                       self.havven_target)
                else:
                    # If we do not have havvens, but we have some escrowed which we can
                    # immediately free, free them.
                    available_havvens = self.available_escrowed_havvens()
                    if available_havvens > 0:
                        self.unescrow_havvens(self._fraction_(available_havvens))
                    # If we have some nomins we could burn to free up havvens, burn them.
                    if self.unavailable_escrowed_havvens() > 0:
                        # If we have nomins, then we should burn them.
                        if self.available_nomins > 0:
                            self.burn_nomins(self._fraction_(self.available_nomins))
                        # Otherwise, we should buy some to burn, if we can.
                        elif self.available_fiat > 0:
                            self.sell_fiat_for_nomins_with_fee(self._fraction_(self.available_fiat))

            # Price is too low, it should increase: we will buy havvens at a premium.
            elif havven_price < hm.round_decimal(self.havven_target * (Dec(1) - self.tolerance)):
                # Buy some if we have fiat to buy it with.
                if self.available_fiat > 0:
                    self.place_havven_fiat_bid_with_fee(self._fraction_(self.available_fiat),
                                                       self.havven_target)
                else:
                    # If we have some nomins, sell them for fiat
                    if self.available_nomins > 0:
                        self.sell_nomins_for_fiat_with_fee(self._fraction_(self.available_nomins))
                    else:
                        # If we have some havvens we could escrow to get nomins, escrow them.
                        if self.available_havvens > 0:
                            self.escrow_havvens(self._fraction_(self.available_havvens))
                            # If we have remaining issuance capacity, then issue some nomins to sell.
                            issuance_rights = self.remaining_issuance_rights()
                            if issuance_rights > 0:
                                self.issue_nomins(issuance_rights)

        if self.nomin_target is not None:
            nomin_price = self.nomin_fiat_market.price
            # Price is too high, it should decrease: we will sell nomins at a discount.
            if nomin_price > hm.round_decimal(self.nomin_target * (Dec(1) + self.tolerance)):
                if self.available_nomins > 0:
                    self.place_nomin_fiat_ask_with_fee(self._fraction_(self.available_nomins),
                                                       self.nomin_target)
                else:
                    # If we have some havvens, we can issue nomins on the back of them to sell.
                    if self.available_havvens > 0:
                        self.escrow_havvens(self._fraction_(self.available_havvens))
                        issuance_rights = self.remaining_issuance_rights()
                        if issuance_rights > 0:
                            self.issue_nomins(issuance_rights)
                    # Otherwise, obtain some.
                    else:
                        self.sell_fiat_for_havvens_with_fee(self._fraction_(self.available_fiat))

            # Price is too low, it should increase: we will buy nomins at a premium.
            elif nomin_price < hm.round_decimal(self.nomin_target * (Dec(1) - self.tolerance)):
                if self.available_fiat > 0:
                    self.place_nomin_fiat_bid_with_fee(self._fraction_(self.available_fiat),
                                                       self.nomin_target)
                else:
                    if self.available_havvens > 0:
                        self.sell_havvens_for_fiat_with_fee(self._fraction_(self.available_havvens))
                    else:
                        # If we do not have havvens, but we have some escrowed which we can
                        # immediately free, free them.
                        available_havvens = self.available_escrowed_havvens()
                        if available_havvens > 0:
                            self.unescrow_havvens(self._fraction_(available_havvens))
                        # If we have some nomins we could burn to free up havvens, burn them.
                        if self.unavailable_escrowed_havvens() > 0:
                            # If we have nomins, then we should burn them.
                            if self.available_nomins > 0:
                                self.burn_nomins(self._fraction_(self.available_nomins))
