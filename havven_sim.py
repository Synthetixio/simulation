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
from mesa.datacollection import DataCollector
from mesa.batchrunner import BatchRunner
from mesa.visualization.modules import CanvasGrid
from mesa.visualization.ModularVisualization import ModularServer

class MyAgent(Agent):
    def __init__(self, name, model):
        super().__init__(name, model)

    def step(self):
        print("{} activated".format(self.unique_id))

class MyModel(Model):
    def __init__(self, n_agents):
        super().__init__(n_agents)
        self.dc = DataCollector(model_reporters={"agent_count": lambda m: m.schedule.get_agent_count()},
                                agent_reporters={"name": lambda a: a.unique_id})

        self.schedule = RandomActivation(self)
        self.grid = MultiGrid(10, 10, torus=True)
        for i in range(n_agents):
            a = MyAgent(i, self)
            self.schedule.add(a)
            coords = (random.randrange(0, 10), random.randrange(0, 10))
            self.grid.place_agent(a, coords)

    def step(self):
        self.schedule.step()
        self.dc.collect(self)

params = {"n_agents": range(1, 20)}
batch_run = BatchRunner(MyModel, params, max_steps=10,
                        model_reporters={"n_agents": lambda m: m.schedule.get_agent_count()})
batch_run.run_all()
batch_df = batch_run.get_model_vars_dataframe()
print(batch_df)

def agent_portrayal(agent):
    return {"Shape":  "circle",
            "Filled": "true",
            "Layer":  0,
            "Color":  "red" if agent.unique_id % 2 else "blue",
            "r":      0.5}

grid = CanvasGrid(agent_portrayal, 10, 10, 500, 500)
server = ModularServer(MyModel, [grid], "My Model", {"n_agents": 100})

server.launch()


