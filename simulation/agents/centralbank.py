from typing import Optional
from decimal import Decimal as Dec

from .marketplayer import MarketPlayer

import model
from managers import HavvenManager as hm


class CentralBank(MarketPlayer):
    """Attempts to use its cash reserves to stabilise prices at a certain level."""

    def __init__(self, unique_id: int, havven: "model.Havven",
                 fiat: Dec = Dec(0), curits: Dec = Dec(0),
                 nomins: Dec = Dec(0),
                 curit_target: Optional[Dec] = None,
                 nomin_target: Optional[Dec] = None,
                 curit_nomin_target: Optional[Dec] = None,
                 tolerance: Dec = Dec('0.01')) -> None:

        super().__init__(unique_id, havven, fiat=fiat,
                         curits=curits, nomins=nomins)

        # Note: it only really makes sense to target one of these at a time.
        # And operating on the assumption that arbitrage is working in the market.

        self.curit_target = curit_target
        """The targeted curit/fiat price."""

        self.nomin_target = nomin_target
        """The targeted nomin/fiat price."""

        # TODO: Actually use this
        self.curit_nomin_target = curit_nomin_target
        """The targeted curit/nomin exchange rate."""

        self.tolerance = tolerance
        """The bank will try to correct the price if it strays out of this range."""

    def step(self) -> None:

        self.cancel_orders()

        if self.curit_target is not None:
            curit_price = self.model.market_manager.curit_fiat_market.price
            # Price is too high, it should decrease: we will sell curits at a discount.
            if curit_price > hm.round_decimal(self.curit_target * (Dec(1) + self.tolerance)):
                # If we have curits, sell them.
                if self.curits > 0:
                    self.place_curit_fiat_ask_with_fee(self._fraction_(self.curits),
                                                       self.curit_target)
                else:
                    # If we do not have curits, but we have some escrowed which we can
                    # immediately free, free them.
                    available_curits = self.available_escrowed_curits()
                    if available_curits > 0:
                        self.unescrow_curits(self._fraction_(available_curits))
                    # If we have some nomins we could burn to free up curits, burn them.
                    if self.unavailable_escrowed_curits() > 0:
                        # If we have nomins, then we should burn them.
                        if self.nomins > 0:
                            self.burn_nomins(self._fraction_(self.nomins))
                        # Otherwise, we should buy some to burn, if we can.
                        elif self.fiat > 0:
                            self.sell_fiat_for_nomins_with_fee(self._fraction_(self.fiat))

            # Price is too low, it should increase: we will buy curits at a premium.
            elif curit_price < hm.round_decimal(self.curit_target * (Dec(1) - self.tolerance)):
                # Buy some if we have fiat to buy it with.
                if self.fiat > 0:
                    self.place_curit_fiat_bid_with_fee(self._fraction_(self.fiat),
                                                       self.curit_target)
                else:
                    # If we have some nomins, sell them for fiat
                    if self.nomins > 0:
                        self.sell_nomins_for_fiat_with_fee(self._fraction_(self.nomins))
                    else:
                        # If we have some curits we could escrow to get nomins, escrow them.
                        if self.curits > 0:
                            self.escrow_curits(self._fraction_(self.curits))
                            # If we have remaining issuance capacity, then issue some nomins to sell.
                            issuance_rights = self.remaining_issuance_rights()
                            if issuance_rights > 0:
                                self.issue_nomins(issuance_rights)

        if self.nomin_target is not None:
            nomin_price = self.model.market_manager.nomin_fiat_market.price
            # Price is too high, it should decrease: we will sell nomins at a discount.
            if nomin_price > hm.round_decimal(self.nomin_target * (Dec(1) + self.tolerance)):
                if self.nomins > 0:
                    self.place_nomin_fiat_ask_with_fee(self._fraction_(self.nomins),
                                                       self.nomin_target)
                else:
                    # If we have some curits, we can issue nomins on the back of them to sell.
                    if self.curits > 0:
                        self.escrow_curits(self._fraction_(self.curits))
                        issuance_rights = self.remaining_issuance_rights()
                        if issuance_rights > 0:
                            self.issue_nomins(issuance_rights)
                    # Otherwise, obtain some.
                    else:
                        self.sell_fiat_for_curits_with_fee(self._fraction_(self.fiat))

            # Price is too low, it should increase: we will buy nomins at a premium.
            elif nomin_price < hm.round_decimal(self.nomin_target * (Dec(1) - self.tolerance)):
                if self.fiat > 0:
                    self.place_nomin_fiat_bid_with_fee(self._fraction_(self.fiat),
                                                       self.nomin_target)
                else:
                    if self.curits > 0:
                        self.sell_curits_for_fiat_with_fee(self._fraction_(self.curits))
                    else:
                        # If we do not have curits, but we have some escrowed which we can
                        # immediately free, free them.
                        available_curits = self.available_escrowed_curits()
                        if available_curits > 0:
                            self.unescrow_curits(self._fraction_(available_curits))
                        # If we have some nomins we could burn to free up curits, burn them.
                        if self.unavailable_escrowed_curits() > 0:
                            # If we have nomins, then we should burn them.
                            if self.nomins > 0:
                                self.burn_nomins(self._fraction_(self.nomins))
