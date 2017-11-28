from typing import Optional, Tuple
from decimal import Decimal as Dec
import random

import orderbook as ob
from managers import HavvenManager as hm
from .marketplayer import MarketPlayer


class Banker(MarketPlayer):
    """Wants to buy havvens and issue nomins, in order to accrue fees."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fiat_havven_order: Optional[Tuple[int, "ob.Bid"]] = None
        """The time the order was placed as well as the fiat/hvn order"""
        self.nomin_havven_order: Optional[Tuple[int, "ob.Bid"]] = None
        self.nomin_fiat_order: Optional[Tuple[int, "ob.Ask"]] = None
        self.sell_rate: Dec = hm.round_decimal(Dec(random.random()/3 + 0.1))
        self.trade_premium: Dec = Dec('0.01')
        self.trade_duration: int = 10
        # step when initialised so nomins appear on the market.
        self.step()

    def setup(self, init_value: Dec):
        endowment = hm.round_decimal(init_value * Dec(4))
        self.fiat = init_value
        self.model.endow_havvens(self, endowment)

    def step(self) -> None:
        if self.nomin_havven_order is not None:
            if self.model.manager.time >= self.nomin_havven_order[0] + self.trade_duration:
                self.nomin_havven_order[1].cancel()
                self.nomin_havven_order = None
        if self.nomin_fiat_order is not None:
            if self.model.manager.time >= self.nomin_fiat_order[0] + self.trade_duration:
                self.nomin_fiat_order[1].cancel()
                self.nomin_fiat_order = None
        if self.fiat_havven_order is not None:
            if self.model.manager.time >= self.fiat_havven_order[0] + self.trade_duration:
                self.fiat_havven_order[1].cancel()
                self.fiat_havven_order = None

        if self.available_nomins > 0:
            if len(self.model.datacollector.model_vars['0']) > 0:
                havven_supply = self.model.datacollector.model_vars['Havven Supply'][-1]
                fiat_supply = self.model.datacollector.model_vars['Fiat Supply'][-1]
                # buy into the market with more supply, as by virtue of there being more supply,
                # the market will probably have a better price...
                if havven_supply > fiat_supply:
                    self.nomin_havven_order = (
                        self.model.manager.time,
                        self.place_havven_nomin_bid_with_fee(
                            self.available_nomins*self.sell_rate,
                            self.havven_nomin_market.price * (Dec(1)-self.trade_premium)
                        )
                    )
                else:
                    self.nomin_fiat_order = (
                        self.model.manager.time,
                        self.place_nomin_fiat_ask_with_fee(
                            self.available_nomins*self.sell_rate,
                            self.nomin_fiat_market.price * (Dec(1)+self.trade_premium)
                        )
                    )

        if self.available_fiat > 0 and not self.fiat_havven_order:
            self.fiat_havven_order = (
                self.model.manager.time,
                self.place_havven_fiat_bid_with_fee(
                    hm.round_decimal(self.available_fiat * self.sell_rate),
                    self.havven_fiat_market.price * (Dec(1)-self.trade_premium)
                )
            )

        if self.available_havvens > 0:
            self.escrow_havvens(self.available_havvens)

        issuable = self.max_issuance_rights() - self.issued_nomins
        if hm.round_decimal(issuable) > 0:
            self.issue_nomins(issuable)
