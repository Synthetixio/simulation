import random

import numpy as np
from scipy.stats import skewnorm

from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector


class MoneyAgent(Agent):
    """An agent with a fixed initial wealth."""
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.wealth = int(skewnorm.rvs(100)*10)

    def move(self):
        steps = self.model.grid.get_neighborhood(self.pos, moore=True)
        new_pos = random.choice(steps)
        self.model.grid.move_agent(self, new_pos)

    def donate(self):
        if self.wealth == 0:
            return

        others = [a for a in self.model.grid.get_cell_list_contents([self.pos]) if a.wealth < self.wealth and a is not self]
        if len(others) > 0:
            other = random.choice(others)
            other.wealth += 1
            self.wealth -= 1

    def step(self):
        self.move()
        self.donate()
    
def wealth_sd(model):
    agents = model.schedule.agents
    num_agents = len(agents)

    mean_wealth = sum([a.wealth for a in agents])/num_agents
    sum_squared_diffs = sum([(a.wealth - mean_wealth)**2 for a in agents])

    return (sum_squared_diffs/(num_agents - 1))**0.5

def gini(model):
    n, s_wealth = len(model.schedule.agents), sorted([a.wealth for a in model.schedule.agents])
    return 1 + (1/n) - 2*(sum(x*(n-i) for i, x in enumerate(s_wealth)) / (n*sum(s_wealth)))

def max_wealth(model):
    w = [a.wealth for a in model.schedule.agents]
    return max(w)

def min_wealth(model):
    w = [a.wealth for a in model.schedule.agents]
    return min(w)

class MoneyModel(Model):
    """A model with some number of agents."""
    def __init__(self, N, width, height):
        self.running = True
        self.schedule = RandomActivation(self)
        self.grid = MultiGrid(width, height, True)

        self.num_agents = N
        for i in range(self.num_agents):
            a = MoneyAgent(i, self)
            self.schedule.add(a)

            x = random.randrange(1, self.grid.width)
            y = random.randrange(1, self.grid.height)
            self.grid.place_agent(a, (x, y))

        self.collector = DataCollector(model_reporters={"Gini": gini,
                                                        "Wealth SD": wealth_sd,
                                                        "Max Wealth": max_wealth,
                                                        "Min Wealth": min_wealth},
                                       agent_reporters={"Wealth": lambda a: a.wealth})

    def step(self):
        """Advance the model by one step."""
        self.collector.collect(self)
        self.schedule.step()

def cell_counts(model):
    dimensions = (model.grid.width, model.grid.height)
    counts = np.zeros(dimensions)
    for cell, x, y in model.grid.coord_iter():
        counts[x][y] = len(cell)
    return counts

def cell_wealth(model):
    dimensions = (model.grid.width, model.grid.height)
    counts = np.zeros(dimensions)
    for cell, x, y in model.grid.coord_iter():
        counts[x][y] = sum(a.wealth for a in cell)
    return counts