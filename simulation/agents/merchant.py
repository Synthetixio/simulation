from .marketplayer import MarketPlayer
from decimal import Decimal as Dec

from typing import Dict, Union
import random


class Merchant(MarketPlayer):
    """
    A merchant market player, this represents someone who
    sells goods/services for Nomins

    inventory/restocking will be dealt with using FIAT

    Starts with an initial inventory, stock level goal,
    updates stock every few ticks

    As nomin->fiat is a percentage, transfer all nomin to fiat
    every step
    """
    inventory: Dict[str, Dict[str, Dec]] = {
        # name: price(nomin), stock_price(fiat), current_stock, stock_goal
        '1': {'price': Dec('14.95'), 'stock_price': Dec('9.95'), 'current_stock': Dec(100), 'stock_goal': Dec(100)},
        '2': {'price': Dec('12.20'), 'stock_price': Dec('6.95'), 'current_stock': Dec(200), 'stock_goal': Dec(200)},
        '3': {'price': Dec('3.50'), 'stock_price': Dec('1.20'), 'current_stock': Dec(300), 'stock_goal': Dec(300)}
    }
    last_restock = 1
    restock_tick_rate = 25

    def step(self):
        if self.available_nomins:
            self.sell_nomins_for_fiat_with_fee(self.available_nomins)

        self.last_restock += 1
        if self.last_restock > self.restock_tick_rate:
            for item in self.inventory:
                info = self.inventory[item]
                to_restock = info['stock_goal'] - info['current_stock']
                cost = to_restock*info['stock_price']
                if self.available_fiat > cost:
                    self.fiat -= cost
                    self.inventory[item]['current_stock'] += to_restock
                else:
                    print(item, info, to_restock, cost, self.fiat, self.available_fiat)
                    raise Exception("Merchant outta money???")

    def sell_stock(self, agent: 'Buyer', item: str, quantity: Dec) -> Dec:
        if agent.available_nomins > self.inventory[item]['price']*quantity and \
                self.inventory[item]['current_stock'] > quantity:
            self.inventory[item]['current_stock'] -= quantity
            return self.inventory[item]['price']*quantity
        return Dec(0)


class Buyer(MarketPlayer):
    inventory = {}

    def __init__(self, merchants, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.merchants = merchants

    def step(self):
        if self.available_fiat:
            self.sell_fiat_for_nomins_with_fee(self.available_fiat)
        i = random.random()
        if i > 0.75:
            to_buy = int(random.random()*5)+1
            buying_from = random.choice(self.merchants)
            buying = random.choice(list(buying_from.inventory.keys()))
            amount = buying_from.sell_stock(self, buying, Dec(to_buy))
            if amount > 0:
                fee = self.model.fee_manager.transferred_nomins_fee(amount)
                self.transfer_nomins_to(buying_from, amount, fee)
                try:
                    self.inventory[buying] += to_buy
                except KeyError:
                    self.inventory[buying] = to_buy
