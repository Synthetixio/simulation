from typing import Optional
from decimal import Decimal as Dec
import random
from scipy.stats import skewnorm

import orderbook as ob
from managers import HavvenManager as hm
from .marketplayer import MarketPlayer


class Banker(MarketPlayer):
    """Wants to buy havvens and issue nomins, in order to accrue fees."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fiat_havven_order: Optional["ob.Bid"] = None
        self.nomin_havven_order: Optional["ob.Bid"] = None
        self.sell_rate: Dec = hm.round_decimal(Dec(random.random()/3 + 0.1))
        # step when initialised so nomins appear on the market.
        self.step()

    def setup(self, init_value: Dec):
        endowment = hm.round_decimal(init_value * Dec(4))
        self.fiat = init_value
        self.model.endow_havvens(self, endowment)

    def step(self) -> None:
        if self.available_nomins > 0:
            if len(self.model.datacollector.model_vars['0']) > 0:
                havven_supply = self.model.datacollector.model_vars['Havven Supply'][-1]
                fiat_supply = self.model.datacollector.model_vars['Fiat Supply'][-1]
                if havven_supply > fiat_supply:
                    self.place_havven_nomin_ask_with_fee(
                        self.available_nomins*self.sell_rate,
                        self.havven_nomin_market.price * Dec('1.01')
                    )
                else:
                    self.place_nomin_fiat_bid_with_fee(
                        self.available_nomins*self.sell_rate,
                        self.havven_fiat_market.price * Dec('0.99')
                    )

        if self.available_fiat > 0:
            self.sell_fiat_for_havvens_with_fee(hm.round_decimal(self.available_fiat * self.sell_rate))

        if self.available_havvens > 0:
            self.escrow_havvens(self.available_havvens)

        issuable = self.max_issuance_rights() - self.issued_nomins
        if hm.round_decimal(issuable) > 0:
            self.issue_nomins(issuable)
