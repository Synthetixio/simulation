import random

import numpy as np
from scipy.stats import skewnorm

from mesa import Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector

import orderbook
import modelstats
from agents import MarketPlayer, Banker


class Havven(Model):
    """
    An agent-based model of the Havven stablecoin system. This class will provide the basic
    market functionality of havven, an exchange, and a place for the market agents to live and
    interact.
    The aim is to stabilise the nomin price, but we would also like to measure other quantities
    including liquidity, volatility, wealth concentration, velocity of money and so on.
    """

    def __init__(self, N, max_fiat_endowment=1000, match_on_order=True) -> None:
        # Mesa setup
        self.running = True
        self.schedule = RandomActivation(self)
        self.datacollector = DataCollector(model_reporters={"Havven Nomins": lambda havven: havven.nomins,
                                                            "Havven Curits": lambda havven: havven.curits,
                                                            "Havven Fiat": lambda havven: havven.fiat,
                                                            "Gini": modelstats.gini,
                                                            "Nomins": lambda havven: havven.nomin_supply,
                                                            "Escrowed Curits": lambda havven: havven.escrowed_curits,
                                                            "Wealth SD": modelstats.wealth_sd,
                                                            "Max Wealth": modelstats.max_wealth,
                                                            "Min Wealth": modelstats.min_wealth,
                                                            "Profit %": modelstats.mean_profit_percentage,
                                                            "Curit Demand": modelstats.curit_demand,
                                                            "Curit Supply": modelstats.curit_supply,
                                                            "Nomin Demand": modelstats.nomin_demand,
                                                            "Nomin Supply": modelstats.nomin_supply,
                                                            "Fiat Demand": modelstats.fiat_demand,
                                                            "Fiat Supply": modelstats.fiat_supply,
                                                            "Fee Pool": lambda havven: havven.nomins,
                                                            "Fees Distributed": lambda havven: havven.fees_distributed},
                                           agent_reporters={"Wealth": lambda a: a.wealth})
        self.time = 1

        # Market variables

        # Prices in fiat per token
        self.curit_price = 1.0
        self.nomin_price = 1.0

        # Money Supply
        self.curit_supply = 10.0**9
        self.nomin_supply = 0.0
        self.escrowed_curits = 0.0
        
        # Havven's own capital supplies
        self.curits = self.curit_supply
        self.nomins = 0
        self.fiat = 0

        # Fees
        self.fee_period = 50
        self.fees_distributed = 0.0
        self.nom_transfer_fee_rate = 0.005
        self.cur_transfer_fee_rate = 0.01
        # TODO: charge issuance and redemption fees
        self.issuance_fee_rate = 0.01
        self.redemption_fee_rate = 0.02
        # TODO: Move fiat fees and currency pool into its own object
        self.fiat_transfer_fee_rate = 0.0

        # Utilisation Ratio maximum (between 0 and 1)
        self.utilisation_ratio_max = 1.0

        # If true, match orders whenever an order is posted,
        # otherwise do so at the end of each period
        self.match_on_order = match_on_order

        # Order books
        # If a book is X_Y_market, then buyers hold X and sellers hold Y.
        self.nom_cur_market = orderbook.OrderBook("NOM/CUR", self.nom_cur_match, self.match_on_order)
        self.fiat_cur_market = orderbook.OrderBook("FIAT/CUR", self.fiat_cur_match, self.match_on_order)
        self.fiat_nom_market = orderbook.OrderBook("FIAT/NOM", self.fiat_nom_match, self.match_on_order)

        # Add the market participants
        total_endowment = 0
        self.num_agents = N
        for i in range(self.num_agents):
            endowment = int(skewnorm.rvs(100)*max_fiat_endowment)
            a = Banker(i, self, fiat=endowment)
            self.schedule.add(a)
            total_endowment += endowment

        reserve_bank = MarketPlayer(self.num_agents, self, 0)
        self.endow_curits(reserve_bank, 6 * N * max_fiat_endowment)
        self.schedule.add(reserve_bank)
        reserve_bank.sell_curits_for_fiat(N * max_fiat_endowment * 3)
        reserve_bank.sell_curits_for_nomins(N * max_fiat_endowment * 3)

    def fiat_value(self, curits, nomins, fiat):
        """Return the equivalent fiat value of the given currency basket."""
        return self.cur_to_fiat(curits) + self.nom_to_fiat(nomins) + fiat

    def endow_curits(self, agent:MarketPlayer, curits:int):
        """Grant an agent an endowment of curits."""
        if curits > 0:
            value = min(self.curits, curits)
            agent.curits += value
            self.curits -= value

    def __bid_ask_match__(self, bid, ask, bid_success, ask_success, bid_transfer, ask_transfer) -> bool:
        """
        Trade between the given bid and ask if they can, with the given transfer and success functions.
        Cancel any orders which the agent cannot afford to service.
        """
        if ask.price > bid.price:
            return False
        
        # Price will be favourable to whoever went second.
        # The earlier poster trades at their posted price,
        # while the later poster transacts at a price no worse than posted; they may do better.
        price = ask.price if ask.time < bid.time else bid.price
        quantity = min(ask.quantity, bid.quantity)
        buy_val = quantity*price

        # Only perform the actual transfer if it would be successful.
        # Cancel any orders that would not succeed.
        fail = False
        if not bid_success(bid.issuer, buy_val):
            bid.cancel()
            fail = True
        if not ask_success(ask.issuer, quantity):
            ask.cancel()
            fail = True
        if fail:
            return False
        
        # Perform the actual transfers
        bid_transfer(bid.issuer, ask.issuer, buy_val)
        ask_transfer(ask.issuer, bid.issuer, quantity)

        # Update the orders, cancelling any with 0 remaining quantity.
        ask.update_quantity(ask.quantity - quantity)
        bid.update_quantity(bid.quantity - quantity)

        return True

    def nom_cur_match(self, bid, ask) -> bool:
        """Buyer offers nomins in exchange for curits from the seller."""
        return self.__bid_ask_match__(bid, ask,
                                      self.transfer_nomins_success,
                                      self.transfer_curits_success,
                                      self.transfer_nomins,
                                      self.transfer_curits)

    def fiat_cur_match(self, bid, ask) -> bool:
        """Buyer offers fiat in exchange for curits from the seller."""
        return self.__bid_ask_match__(bid, ask,
                                      self.transfer_fiat_success,
                                      self.transfer_curits_success,
                                      self.transfer_fiat,
                                      self.transfer_curits)

    def fiat_nom_match(self, bid, ask) -> bool:
        """Buyer offers fiat in exchange for nomins from the seller."""
        return self.__bid_ask_match__(bid, ask,
                                      self.transfer_fiat_success,
                                      self.transfer_nomins_success,
                                      self.transfer_fiat,
                                      self.transfer_nomins)

    def transfer_fiat_fee(self, value):
        return value * self.fiat_transfer_fee_rate

    def transfer_curits_fee(self, value):
        return value * self.cur_transfer_fee_rate

    def transfer_nomins_fee(self, value):
        return value * self.nom_transfer_fee_rate

    def transfer_fiat_success(self, sender:MarketPlayer, value:float) -> bool:
        """True iff the sender could successfully send a value of fiat."""
        return 0 <= value + self.transfer_fiat_fee(value) <= sender.fiat
    
    def transfer_curits_success(self, sender:MarketPlayer, value:float) -> bool:
        """True iff the sender could successfully send a value of curits."""
        return 0 <= value + self.transfer_curits_fee(value) <= sender.curits
    
    def transfer_nomins_success(self, sender:MarketPlayer, value:float) -> bool:
        """True iff the sender could successfully send a value of nomins."""
        return 0 <= value + self.transfer_nomins_fee(value) <= sender.nomins

    def max_transferrable_fiat(self, principal):
        """A user can transfer slightly less than their total balance when fees are taken into account."""
        return principal / (1 + self.fiat_transfer_fee_rate)

    def max_transferrable_curits(self, principal):
        """A user can transfer slightly less than their total balance when fees are taken into account."""
        return principal / (1 + self.cur_transfer_fee_rate)

    def max_transferrable_nomins(self, principal):
        """A user can transfer slightly less than their total balance when fees are taken into account."""
        return principal / (1 + self.nom_transfer_fee_rate)

    def transfer_fiat(self, sender:MarketPlayer, recipient:MarketPlayer, value:float) -> bool:
        """Transfer a positive value of fiat currency from the sender to the recipient, if balance is sufficient.
        Return True on success."""
        if self.transfer_fiat_success(sender, value):
            fee = self.transfer_fiat_fee(value)
            sender.fiat -= value + fee
            recipient.fiat += value
            self.fiat += fee
            return True
        return False
    
    def transfer_curits(self, sender:MarketPlayer, recipient:MarketPlayer, value:float) -> bool:
        """Transfer a positive value of curits from the sender to the recipient, if balance is sufficient.
        Return True on success."""
        if self.transfer_curits_success(sender, value):
            fee = self.transfer_curits_fee(value)
            sender.curits -= value + fee
            recipient.curits += value
            self.curits += fee
            return True
        return False
    
    def transfer_nomins(self, sender:MarketPlayer, recipient:MarketPlayer, value:float) -> bool:
        """Transfer a positive value of nomins from the sender to the recipient, if balance is sufficient.
        Return True on success."""
        if self.transfer_nomins_success(sender, value):
            fee = self.transfer_nomins_fee(value)
            sender.nomins -= value + fee
            recipient.nomins += value
            self.nomins += fee
            return True
        return False 

    def cur_to_nom(self, value:float) -> float:
        """Convert a quantity of curits to its equivalent value in nomins."""
        return (value * self.curit_price) / self.nomin_price
    
    def cur_to_fiat(self, value:float) -> float:
        """Convert a quantity of curits to its equivalent value in fiat."""
        return value * self.curit_price
    
    def nom_to_cur(self, value:float) -> float:
        """Convert a quantity of nomins to its equivalent value in curits."""
        return (value * self.nomin_price) / self.curit_price

    def nom_to_fiat(self, value:float) -> float:
        """Convert a quantity of nomins to its equivalent value in fiat."""
        return value * self.nomin_price

    def fiat_to_cur(self, value:float) -> float:
        """Convert a quantity of fiat to its equivalent value in curits."""
        return value / self.curit_price

    def fiat_to_nom(self, value:float) -> float:
        """Convert a quantity of fiat to its equivalent value in nomins."""
        return value / self.nomin_price

    def distribute_fees(self):
        """Distribute currently held nomins to holders of curits."""
        # Different fee modes:
        #  * distributed by held curits
        # TODO: * distribute by escrowed curits
        # TODO: * distribute by issued nomins
        # TODO: * distribute by motility

        pre_fees = self.nomins
        for agent in self.schedule.agents:
            if self.nomins == 0:
                break
            qty = min(agent.issued_nomins / self.nomins, self.nomins)
            agent.nomins += qty
            self.nomins -= qty
            self.fees_distributed += qty
    
    def step(self) -> None:
        """Advance the model by one step."""
        # Agents submit trades
        self.schedule.step()

        # Collect data
        self.datacollector.collect(self)

        # Resolve outstanding trades
        if not self.match_on_order:
            self.nom_cur_market.match()
            self.fiat_cur_market.match()
            self.fiat_nom_market.match()

        # Distribute fees periodically.
        if (self.time % self.fee_period) == 0:
            self.distribute_fees()

        self.time += 1