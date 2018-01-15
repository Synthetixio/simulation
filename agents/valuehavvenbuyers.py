from agents import MarketPlayer

from decimal import Decimal as Dec


class ValueHavvenBuyers(MarketPlayer):
    """
    The ValueHavvenBuyers wait until the underlying value of havvens
      is worth more than the current market price

    This would happen when copt/cmax are close to 1

    They then wait for the market to catch up to the real value of havvens
      and then sell them back in
    """
    havven_fiat_trade = None
    discount_purchase_rate = Dec('0.85')
    'At what "value" do they purchase the havvens'


    def setup(self, init_value: Dec) -> None:
        self.fiat = init_value * Dec(4)

    def step(self) -> None:
        if self.havven_fiat_trade:
            self.havven_fiat_trade.cancel()
            self.havven_fiat_trade = None

        havven_value_multiplier = self.havven_value_calculation()

        # just place their value trade every step, instead of checking if the current market conditions are good
        price = (Dec(1) / havven_value_multiplier) * self.havven_fiat_market.price * self.discount_purchase_rate
        print(price)
        self.havven_fiat_trade = self.place_havven_fiat_bid(self.fiat/price, price)

    def havven_value_calculation(self) -> Dec:
        return self.model.mint.cmax * self.nomin_fiat_market.price / self.havven_fiat_market.price
