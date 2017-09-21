"""
havven_sim.py

This will be an agent-based model of the Havven system.

It must incorporate three parts: 

* The currency environment itself;
* An exchange to go between NOM, CUR, and USD;
* The agents themselves.
"""


# What follows is just a prototype to demonstrate that the mesa ABM module works.

import random

from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid

import numpy as np
import matplotlib.pyplot as plt

class MoneyAgent(Agent):
    """An agent with a fixed initial wealth."""
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.wealth = random.randrange(0,10)

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

class MoneyModel(Model):
    """A model with some number of agents."""
    def __init__(self, N, width, height):
        self.schedule = RandomActivation(self)
        self.grid = MultiGrid(width, height, True)

        self.num_agents = N
        for i in range(self.num_agents):
            a = MoneyAgent(i, self)
            self.schedule.add(a)

            x = random.randrange(1, self.grid.width)
            y = random.randrange(1, self.grid.height)
            self.grid.place_agent(a, (x, y))
    
    def wealth_sd(self):
        agents = self.schedule.agents
        num_agents = len(agents)

        mean_wealth = sum([a.wealth for a in agents])/num_agents
        sum_squared_diffs = sum([(a.wealth - mean_wealth)**2 for a in agents])

        return (sum_squared_diffs/(num_agents - 1))**0.5

    def step(self):
        """Advance the model by one step."""

        print("Wealth standard deviation: {}".format(self.wealth_sd()))
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

m = MoneyModel(1000, 50, 50)

plt.ion()
plt.hist([a.wealth for a in m.schedule.agents])
for _ in range(1000):
    m.step()
    plt.cla()
    #plt.hist([a.wealth for a in m.schedule.agents])
    plt.imshow(cell_wealth(m), interpolation='nearest')
    plt.draw()
    plt.pause(0.01)
plt.show()