import random

import numpy as np
from scipy.stats import skewnorm

from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector


class MarketPlayer(Agent):
    """An agent with a fixed initial wealth in dollars, with which it must buy into the market."""

    def __init__(self, unique_id, model, endowment):
        super().__init__(unique_id, model)
        self.dollars = endowment 
        self.curits = 0
        self.nomins = 0

    def wealth(self):
        return self.dollars + self.curits*self.model.curit_price + self.nomins*self.model.nomin_price

    def step(self):
        pass
    
def wealth_sd(model):
    num_agents = len(model.schedule.agents)
    wealths = [a.wealth() for a in model.schedule.agents]
    mean_wealth = sum(wealths)/num_agents
    sum_squared_diffs = sum([(w - mean_wealth)**2 for w in wealths])
    return (sum_squared_diffs/(num_agents - 1))**0.5

def gini(model):
    n, s_wealth = len(model.schedule.agents), sorted([a.wealth() for a in model.schedule.agents])
    return 1 + (1/n) - 2*(sum(x*(n-i) for i, x in enumerate(s_wealth)) / (n*sum(s_wealth)))

def max_wealth(model):
    w = [a.wealth() for a in model.schedule.agents]
    return max(w)

def min_wealth(model):
    w = [a.wealth() for a in model.schedule.agents]
    return min(w)

class HavvenModel(Model):
    """An agent-based model of the Havven stablecoin system."""

    def __init__(self, N, max_endowment=1000):
        self.running = True
        self.schedule = RandomActivation(self)

        self.curit_price = 1.0
        self.nomin_price = 1.0

        self.num_agents = N
        for i in range(self.num_agents):
            endowment = int(skewnorm.rvs(100)*max_endowment)
            a = MarketPlayer(i, self, endowment)
            self.schedule.add(a)

        self.collector = DataCollector(model_reporters={"Gini": gini,
                                                        "Wealth SD": wealth_sd,
                                                        "Max Wealth": max_wealth,
                                                        "Min Wealth": min_wealth},
                                       agent_reporters={"Wealth": lambda a: a.wealth})

    def transfer_dollars(self, sender, recipient, value):
        if (value >= sender.dollars):
            sender.dollars -= value
            recipient.dollars += value

    def transfer_curits(self, sender, recipient, value):
        if (value >= sender.curits):
            sender.curits -= value
            recipient.curits += value

    def transfer_nomins(self, sender, recipient, value):
        if (value >= sender.nomins):
            sender.nomins -= value
            recipient.nomins += value

    def step(self):
        """Advance the model by one step."""
        self.collector.collect(self)
        self.schedule.step()