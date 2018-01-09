"""
merchant.py

A merchant who owns an inventory and restocks it using fiat,
and sells the goods for nomins.

A buyer who receives a wage in fiat, and uses that to purchase
goods with nomins.

The result on the market will be a consistent conversion from
fiat to nomins by the buyers, and a bulk conversion from nomins
to fiat by the merchants.
"""

from .marketplayer import MarketPlayer
from decimal import Decimal as Dec
from collections import defaultdict

from typing import Dict
import random


class Merchant(MarketPlayer):
    """
    A merchant market player, this represents someone who
    sells goods/services for nomins.

    Inventory/restocking will be dealt with using fiat.

    Starts with an initial inventory, stock level goal,
    and updates their stock every few ticks.

    As nomin->fiat fee is a percentage, transfer all nomins to fiat
    every step.
    """

    # the minimal price the merchant will sell nomins for
    minimal_sell_price = Dec('0.9')
    nom_sell_order = None

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # Set up this merchant's inventory of items, their stocks, and their prices.
        self.inventory: Dict[str, Dict[str, Dec]] = {
            # name: price(nomins), stock_price(fiat), current_stock, stock_goal
            str(i): {'price': Dec(random.random() * 20) + 1, 'stock_price': Dec(1),
                     'current_stock': Dec(100), 'stock_goal': Dec(100)}
            for i in range(1, random.randint(4, 6))
        }
        for i in self.inventory:
            self.inventory[i]['stock_price'] = self.inventory[i]['price'] * Dec((random.random() / 3) + 0.5)

        self.last_restock: int = 0
        """Time since the last inventory restock."""

        self.restock_tick_rate: int = random.randint(20, 30)
        """Time between inventory restocking. Randomised to prevent all merchants restocking at once."""

    def setup(self, init_value: Dec):
        self.fiat = init_value

    def step(self) -> None:
        self.last_restock += 1
        if self.last_restock > self.restock_tick_rate:
            self.last_restock = 0

            if self.available_nomins:
                if self.nom_sell_order:
                    self.nom_sell_order.cancel()
                self.nom_sell_order = self.place_nomin_fiat_ask_with_fee(
                    self.available_nomins, self.minimal_sell_price
                )

            for item in self.inventory:
                info = self.inventory[item]
                to_restock = info['stock_goal'] - info['current_stock']
                cost = to_restock * info['stock_price']
                if self.available_fiat > cost:
                    self.fiat -= cost
                    self.inventory[item]['current_stock'] += to_restock
                # if out of money try again in 2 ticks.
                else:
                    amount_possible = int(self.available_fiat / info['stock_price'])
                    self.fiat -= info['stock_price'] * amount_possible
                    self.inventory[item]['current_stock'] += amount_possible

    def sell_stock(self, agent: 'Buyer', item: str, quantity: Dec) -> Dec:
        """
        Function to transfer stock to buyer, telling the buyer how much they
        need to transfer... We can trust the buyer will transfer.
        """
        if agent.available_nomins > self.inventory[item]['price'] * quantity and \
                        self.inventory[item]['current_stock'] > quantity:
            self.inventory[item]['current_stock'] -= quantity
            return self.inventory[item]['price'] * quantity
        return Dec(0)


class Buyer(MarketPlayer):
    """
    Buyer interacts with merchants to purchase goods using nomins.
    Buyers receive a wage in fiat, buy nomins, and then use them to buy goods.
    """
    min_wage = 2
    max_wage = 10
    min_mpc = 0.1  # not Dec as multiplied by floats later
    max_mpc = 0.9

    max_nomin_price = Dec('1.1')

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.inventory = defaultdict(Dec)
        self.wage = random.randint(self.min_wage, self.max_wage)

        self.mpc = (self.max_mpc - self.min_mpc) * random.random() + self.min_mpc
        """This agent's marginal propensity to consume."""

        self.order = None

    def setup(self, init_value: Dec):
        # start with no money, as they have a wage
        self.fiat = 0

    def step(self) -> None:
        # Earn some dough.
        self.fiat += self.wage

        # Buy some crypto.
        if self.available_fiat:
            if self.order and self.order.active:
                self.order.cancel()
            # place a bid at max_nomin_price, as it would be dumb for anyone to pay more
            self.order = self.place_nomin_fiat_bid_with_fee(
                self.available_fiat / self.max_nomin_price, self.max_nomin_price
            )

        # If feeling spendy, buy something.
        if random.random() < self.mpc:
            to_buy = Dec(int(random.random() * 5) + 1)
            buying_from = random.choice(self.model.agent_manager.agents['Merchant'])
            buying = random.choice(list(buying_from.inventory.keys()))
            amount = buying_from.sell_stock(self, buying, Dec(to_buy))
            if amount > 0:
                self.transfer_nomins_to(buying_from, amount)
                self.inventory[buying] += to_buy
