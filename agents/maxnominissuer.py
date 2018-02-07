import random
from decimal import Decimal as Dec
from typing import Optional, Tuple

from managers import HavvenManager as hm
from core import orderbook as ob
from .marketplayer import MarketPlayer


class MaxNominIssuer(MarketPlayer):
    """
    Issues nomins up to c_max, and uses the funds from fees/issuance to buy more havvens
    They trust that havven value will go up, so they should never be too far off 100% escrowed,
      and over time should be able to escrow more, as demand for nomins increases.
    """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fiat_havven_order: Optional[Tuple[int, "ob.Bid"]] = None
        """The time the order was placed as well as the fiat/hvn order"""
        self.nomin_havven_order: Optional[Tuple[int, "ob.Bid"]] = None
        self.nomin_fiat_order: Optional[Tuple[int, "ob.Ask"]] = None
        self.sell_rate: Dec = hm.round_decimal(Dec(random.random() / 3 + 0.1))
        self.trade_premium: Dec = Dec('0.01')
        self.trade_duration: int = 10
        # step when initialised so nomins appear on the market.
        self.step()

    def setup(self, init_value: Dec):
        endowment = hm.round_decimal(init_value * Dec(4))
        self.fiat = init_value
        self.model.endow_havvens(self, endowment)

    def step(self) -> None:
        # clear old and filled orders
        if self.nomin_havven_order is not None and not self.nomin_havven_order[1].active:
            self.nomin_havven_order[1].cancel()
            self.nomin_havven_order = None
        if self.nomin_fiat_order is not None and not self.nomin_fiat_order[1].active:
            self.nomin_fiat_order[1].cancel()
        if self.fiat_havven_order is not None and not self.fiat_havven_order[1].active:
            self.fiat_havven_order[1].cancel()

        if self.available_nomins > 0 and self.nomin_havven_order is not None:
            if len(self.model.datacollector.model_vars['0']) > 0:
                havven_supply = self.model.datacollector.model_vars['Havven Supply'][-1]
                fiat_supply = self.model.datacollector.model_vars['Fiat Supply'][-1]
                # buy into the market with more supply, as by virtue of there being more supply,
                # the market will probably have a better price...
                if havven_supply > fiat_supply:
                    order = self.place_havven_nomin_bid_with_fee(
                        self.available_nomins * self.sell_rate,
                        self.havven_nomin_market.price * (Dec(1) + self.trade_premium)
                    )
                    if order is not None:
                        self.nomin_havven_order = (
                            self.model.manager.time,
                            order
                        )

                else:
                    order = self.place_nomin_fiat_ask_with_fee(
                        self.available_nomins * self.sell_rate,
                        self.nomin_fiat_market.price * (Dec(1) - self.trade_premium)
                    )
                    if order is None:
                        return
                    self.nomin_fiat_order = (
                        self.model.manager.time,
                        order
                    )

        if self.available_fiat > 0 and not self.fiat_havven_order:
            order = self.place_havven_fiat_bid_with_fee(
                hm.round_decimal(self.available_fiat * self.sell_rate),
                self.havven_fiat_market.price * (Dec(1) + self.trade_premium)
            )
            if order is None:
                return
            self.fiat_havven_order = (
                self.model.manager.time,
                order
            )

        if self.available_havvens > 0:
            self.escrow_havvens(self._fraction(self.available_havvens, Dec(5)))
