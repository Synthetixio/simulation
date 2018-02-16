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
    havven_fiat_buy = None
    havven_fiat_sell = None

    minimal_price = Dec('0.1')
    'What is the least they will pay'

    purchase_rate_mutiplier = Dec('1.2')
    'How over "value" do they purchase the havvens'

    sell_rate_multiplier = Dec('5')
    'How over "value" do they sell the havvens'

    def setup(self, wealth_parameter: Dec, wage_parameter: Dec, liquidation_param: Dec) -> None:
        super().setup(wealth_parameter, wage_parameter, liquidation_param)

        self.fiat = wealth_parameter * Dec(4)

    def step(self) -> None:
        super().step()

        if self.havven_fiat_buy:
            self.havven_fiat_buy.cancel()
            self.havven_fiat_buy = None

        if self.havven_fiat_sell:
            self.havven_fiat_sell.cancel()
            self.havven_fiat_sell = None

        havven_value_multiplier = self.havven_value_calculation()

        # just place their value trade every step, instead of checking if the current market conditions are good
        buy_price = havven_value_multiplier * self.havven_fiat_market.price * self.purchase_rate_mutiplier
        buy_price = max(self.minimal_price, buy_price)
        self.havven_fiat_buy = self.place_havven_fiat_bid_with_fee(self.available_fiat/buy_price, buy_price)

        sell_price = havven_value_multiplier * self.havven_fiat_market.price * self.sell_rate_multiplier
        sell_price = max(sell_price, self.sell_rate_multiplier * self.minimal_price)
        self.havven_fiat_sell = self.place_havven_fiat_ask_with_fee(self.available_havvens, sell_price)

    def havven_value_calculation(self) -> Dec:
        return (self.model.mint.cmax * self.nomin_fiat_market.price / self.havven_fiat_market.price) + self.model.mint.intrinsic_havven_value
