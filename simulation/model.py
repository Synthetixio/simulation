import random

import numpy as np
from scipy.stats import skewnorm

from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector


class MarketPlayer(Agent):
    """
    An agent with a fixed initial wealth in fiat, with which it must buy into the market.
    The agent may escrow curits in order to issue nomins, and use various strategies in order
    to trade in the marketplace. Its aim is to increase its own wealth.
    """

    def __init__(self, unique_id, model, endowment):
        super().__init__(unique_id, model)
        self.fiat = endowment 
        self.curits = 0
        self.nomins = 0
        self.escrowed_curits = 0
        self.issued_nomins = 0

    def wealth(self) -> float:
        """Return the total wealth of this agent at current fiat prices."""
        return self.fiat + self.model.cur_to_fiat(self.curits) + self.model.nom_to_fiat(self.nomins)

    def transfer_fiat_to(self, recipient:"MarketPlayer", value:float) -> bool:
        """Transfer a value of fiat to the recipient, if balance is sufficient. Return True on success."""
        return self.model.transfer_fiat(self, recipient, value)
    
    def transfer_curits_to(self, recipient:"MarketPlayer", value:float) -> bool:
        """Transfer a value of curits to the recipient, if balance is sufficient. Return True on success."""
        return self.model.transfer_curits(self, recipient, value)

    def transfer_nomins_to(self, recipient:"MarketPlayer", value:float) -> bool:
        """Transfer a value of nomins to the recipient, if balance is sufficient. Return True on success."""
        return self.model.transfer_nomins(self, recipient, value)

    def escrow_curits(self, value:float) -> bool:
        pass

    def issue_nomins(self, value:float) -> bool:
        pass

    def step(self) -> None:
        pass


# Functions for extracting aggregate information from the Havven model.

def wealth_sd(model:HavvenModel) -> float:
    """Return the standard deviation of wealth in the economy."""
    num_agents = len(model.schedule.agents)
    wealths = [a.wealth() for a in model.schedule.agents]
    mean_wealth = sum(wealths)/num_agents
    sum_squared_diffs = sum([(w - mean_wealth)**2 for w in wealths])
    return (sum_squared_diffs/(num_agents - 1))**0.5

def gini(model:HavvenModel) -> float:
    """Return the gini coefficient in the economy."""
    n, s_wealth = len(model.schedule.agents), sorted([a.wealth() for a in model.schedule.agents])
    return 1 + (1/n) - 2*(sum(x*(n-i) for i, x in enumerate(s_wealth)) / (n*sum(s_wealth)))

def max_wealth(model:HavvenModel) -> float:
    """Return the wealth of the richest person in the economy."""
    w = [a.wealth() for a in model.schedule.agents]
    return max(w)

def min_wealth(model:HavvenModel) -> float:
    """Return the wealth of the poorest person in the economy."""
    w = [a.wealth() for a in model.schedule.agents]
    return min(w)

class HavvenModel(Model):
    """
    An agent-based model of the Havven stablecoin system. This class will provide the basic
    market functionality of havven, an exchange, and a place for the market agents to live and
    interact.
    The aim is to stabilise the nomin price, but we would also like to measure other quantities
    including liquidity, volatility, wealth concentration, velocity of money and so on.
    """

    def __init__(self, N, max_endowment=1000):
        # Mesa setup
        self.running = True
        self.schedule = RandomActivation(self)
        self.collector = DataCollector(model_reporters={"Gini": gini,
                                                        "Wealth SD": wealth_sd,
                                                        "Max Wealth": max_wealth,
                                                        "Min Wealth": min_wealth},
                                       agent_reporters={"Wealth": lambda a: a.wealth})

        # Add the market participants
        self.num_agents = N
        for i in range(self.num_agents):
            endowment = int(skewnorm.rvs(100)*max_endowment)
            a = MarketPlayer(i, self, endowment)
            self.schedule.add(a)

        # Market variables

        # Prices in fiat per token
        self.curit_price = 1.0
        self.nomin_price = 1.0

        # Money Supply
        self.curit_supply = 10.0**9
        self.nomin_supply = 0.0
        self.escrowed_curits = 0.0
        self.issued_nomins = 0.0


    def transfer_fiat(self, sender:MarketPlayer, recipient:MarketPlayer, value:float) -> bool:
        """Transfer a value of fiat currency from the sender to the recipient, if balance is sufficient.
        Return True on success."""
        if (value >= sender.fiat):
            sender.fiat -= value
            recipient.fiat += value
            return True
        return False

    def transfer_curits(self, sender:MarketPlayer, recipient:MarketPlayer, value:float) -> bool:
        """Transfer a value of curits from the sender to the recipient, if balance is sufficient.
        Return True on success."""
        if (value >= sender.curits):
            sender.curits -= value
            recipient.curits += value
            return True
        return False

    def transfer_nomins(self, sender, recipient, value) -> bool:
        """Transfer a value of nomins from the sender to the recipient, if balance is sufficient.
        Return True on success."""
        if (value >= sender.nomins):
            sender.nomins -= value
            recipient.nomins += value
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

    def step(self) -> None:
        """Advance the model by one step."""
        self.collector.collect(self)
        self.schedule.step()