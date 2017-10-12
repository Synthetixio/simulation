from typing import Optional
import random

import orderbook as ob
from .marketplayer import MarketPlayer

class Banker(MarketPlayer):
    """Wants to buy curits and issue nomins, in order to accrue fees."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fiat_curit_order: Optional["ob.Bid"] = None
        self.nomin_curit_order: Optional["ob.Bid"] = None
        self.rate: float = random.random() * 0.05

    def step(self) -> None:
        if self.fiat > 0:
            if self.fiat_curit_order:
                self.fiat_curit_order.cancel()
            fiat = self.model.fee_manager.max_transferrable_fiat(self.fiat)
            self.fiat_curit_order = self.sell_fiat_for_curits(fiat * self.rate)

        if self.nomins > 0:
            if self.nomin_curit_order:
                self.nomin_curit_order.cancel()
            nomins = self.model.fee_manager.max_transferrable_nomins(self.nomins)
            self.nomin_curit_order = self.sell_nomins_for_curits(nomins)

        if self.curits > 0:
            self.escrow_curits(self.curits)

        issuable = self.max_issuance_rights() - self.issued_nomins
        if issuable > 0:
            self.issue_nomins(issuable)

