from typing import Optional, Union

from .marketplayer import MarketPlayer

import model
import orderbook as ob

class CentralBank(MarketPlayer):
    """Attempts to use its cash reserves to stabilise prices at a certain level."""
    
    def __init__(self, unique_id: int, havven: "model.Havven",
                 curit_target: Optional[float] = None,
                 nomin_target: Optional[float] = None,
                 curit_nomin_target: Optional[float] = None,
                 tolerance: float = 0.01) -> None:

        super().__init__(unique_id, havven)

        self.curit_target = curit_target
        """The targeted curit/fiat price."""

        self.nomin_target = nomin_target
        """The targeted nomin/fiat price."""

        self.curit_nomin_target = curit_nomin_target
        """The targeted curit/nomin exchange rate."""
        
        self.tolerance = tolerance
        """The bank will try to correct the price if it strays out of this range."""

        self.curit_order: Optional["ob.LimitOrder"] = None
        self.nomin_order: Optional["ob.LimitOrder"] = None

        # TODO: Actually use this
        self.curit_nomin_order: Optional["ob.LimitOrder"] = None

    def step(self) -> None:
        curit_price = self.model.market_manager.curit_fiat_market.price
        if self.curit_target is not None:
            if curit_price > self.curit_target * (1 + self.tolerance):
                # Price is too high, it should decrease: we will sell curits at a discount.
                if self.curits > 0 and self.curit_order is not None:
                    self.curit_order = self.place_curit_fiat_ask_with_fee(self.curits / 2, self.curit_target)
            elif curit_price < self.curit_target * (1 - self.tolerance):
                # Price is too low, it should increase: we will buy curits at a premium.
                if self.fiat > 0 and self.curit_order is not None:
                    self.curit_order = self.place_curit_fiat_bid_with_fee(self.fiat / 2, self.curit_target)
            else:
                # Price does not need stabilisation, cancel orders.
                if self.curit_order is not None:
                    self.curit_order.cancel()
                    self.curit_order = None

        nomin_price = self.model.market_manager.nomin_fiat_market.price
        if self.nomin_target is not None:
            if nomin_price > self.nomin_target * (1 + self.tolerance):
                # Price is too high, it should decrease: we will sell curits at a discount.
                if self.nomins > 0 and self.nomin_order is not None:
                    self.nomin_order = self.place_nomin_fiat_ask_with_fee(self.nomins / 2, self.nomin_target)
            elif nomin_price < self.nomin_target * (1 - self.tolerance):
                # Price is too low, it should increase: we will buy curits at a premium.
                if self.fiat > 0 and self.nomin_order is not None:
                    self.nomin_order = self.place_nomin_fiat_bid_with_fee(self.fiat / 2, self.nomin_target)
            else:
                # Price does not need stabilisation, cancel orders.
                if self.nomin_order is not None:
                    self.nomin_order.cancel()
                    self.nomin_order = None
