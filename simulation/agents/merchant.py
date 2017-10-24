"""
merchant.py

A merchant who owns an inventory and restocks it using fiat,
and sells the goods for nomin

A buyer who receives a wage in fiat, and uses that to purchase
goods with nomin

The result on the market will be a consistent conversion from
fiat to nomin by the buyers, and a bulk conversion from nomin
to fiat by the merchants
"""

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.inventory: Dict[str, Dict[str, Dec]] = {
            # name: price(nomin), stock_price(fiat), current_stock, stock_goal
            str(i): {'price': Dec(random.random() * 20), 'stock_price': 1,
                     'current_stock': Dec(100), 'stock_goal': Dec(100)}
            for i in range(1, random.randint(4, 6))
        }
        for i in self.inventory:
            self.inventory[i]['stock_price'] = self.inventory[i]['price'] * Dec((random.random() / 3) + 0.5)

        self.last_restock = 1  # random.randint(0,25)
        self.restock_tick_rate = 25

    def step(self):
        self.last_restock += 1
        if self.last_restock > self.restock_tick_rate:
            self.last_restock = 0
            self.sell_nomins_for_fiat_with_fee(self.available_nomins)
            for item in self.inventory:
                info = self.inventory[item]
                to_restock = info['stock_goal'] - info['current_stock']
                cost = to_restock*info['stock_price']
                if self.available_fiat > cost:
                    self.fiat -= cost
                    self.inventory[item]['current_stock'] += to_restock
                else:
                    print(self.portfolio())
                    print(self.portfolio(True))
                    print(to_restock, cost)
                    raise Exception("Merchant out of money? nom->fiat really bad?")

    def sell_stock(self, agent: 'Buyer', item: str, quantity: Dec) -> Dec:
        if agent.available_nomins > self.inventory[item]['price']*quantity and \
                self.inventory[item]['current_stock'] > quantity:
            self.inventory[item]['current_stock'] -= quantity
            return self.inventory[item]['price']*quantity
        return Dec(0)


class Buyer(MarketPlayer):
    """
    Buyer interacts with merchants to purchase their goods using their nomins
    They transfer their fiat->nomins and then use their nomins to buy goods
    """
    inventory = {}

    wage = random.randint(2, 10)

    def __init__(self, merchants, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.merchants = merchants

    def step(self):
        self.fiat += self.wage
        if self.available_fiat:
            self.sell_fiat_for_nomins_with_fee(self.available_fiat)
        i = random.random()
        if i > 0.75:
            to_buy = int(random.random()*5)+1
            buying_from = random.choice(self.merchants)
            buying = random.choice(list(buying_from.inventory.keys()))
            amount = buying_from.sell_stock(self, buying, Dec(to_buy))
            if amount > 0:
                self.transfer_nomins_to(buying_from, amount)
                try:
                    self.inventory[buying] += to_buy
                except KeyError:
                    self.inventory[buying] = to_buy
