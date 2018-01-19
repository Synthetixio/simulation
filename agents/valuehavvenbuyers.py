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

    minimal_price = Dec('0.05')
    'What is the least they will pay'

    purchase_rate = Dec('1.2')
    'How over "value" do they purchase the havvens'

    def setup(self, init_value: Dec) -> None:
        self.wage_parameter = init_value/Dec(100)
        self.fiat = init_value * Dec(4)

    def step(self) -> None:
        super().step()

        if self.havven_fiat_trade:
            self.havven_fiat_trade.cancel()
            self.havven_fiat_trade = None

        havven_value_multiplier = self.havven_value_calculation()

        # just place their value trade every step, instead of checking if the current market conditions are good
        price = havven_value_multiplier * self.havven_fiat_market.price * self.purchase_rate
        price = max(self.minimal_price, price)
        self.havven_fiat_trade = self.place_havven_fiat_bid_with_fee(self.available_fiat/price, price)

    def havven_value_calculation(self) -> Dec:
        return self.model.mint.cmax * self.nomin_fiat_market.price / self.havven_fiat_market.price
