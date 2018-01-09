from agents import MarketPlayer
from decimal import Decimal as Dec


class FeeOptimiser(MarketPlayer):
    def setup(self, wealth_parameter: Dec):
        self.model.endow_havvens(wealth_parameter * 2)

    def step(self):
        if self.collateralisation - self.model.mint.copt > 0.001:
            # over-collateralised, burn nomins
            pass
        elif self.collateralisation - self.model.mint.copt > 0.001:
            # under-collateralised, issue nomins
            pass
        else:
            pass  # otherwise do nothing
