# I run the sim, and the visualisation server.
from mesa.visualization.modules import CanvasGrid
from mesa.visualization.modules import ChartModule
from mesa.visualization.ModularVisualization import ModularServer
from model import MoneyModel

def agent_portrayal(agent):
    max_wealth = 30
    frac = min(255, int(255*agent.wealth / max_wealth))
    color = "#{0:X}{0:X}{1:X}".format(frac, 255 - frac)
    return {"Shape": "rect",
            "w": 1.0,
            "h": 1.0,
            "Filled": "true",
            "Color": color,
            "Layer": 0}


def make_server(n_agents=1000, width=25, height=25, px_width=500, px_height=500):
    grid = CanvasGrid(agent_portrayal, width, height, px_width, px_height)
    chart = ChartModule([{"Label": "Gini",
                          "Color": "red"},
                         {"Label": "Wealth SD",
                          "Color": "blue"}],
                        data_collector_name="collector")

    chart2 = ChartModule([{"Label": "Max Wealth",
                          "Color": "purple"},
                         {"Label": "Min Wealth",
                          "Color": "orange"}],
                       data_collector_name="collector")

    server = ModularServer(MoneyModel, [grid, chart, chart2], "Money Model",
                        {"N": n_agents, "width": width, "height": height})
    return server