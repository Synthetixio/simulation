"""server.py: Functions for setting up the simulation/visualisation server."""

from typing import List

from mesa.visualization.modules import ChartModule
from mesa.visualization.UserParam import UserSettableParameter
from mesa.visualization.ModularVisualization import ModularServer, VisualizationElement

import model

from visualization.mesa_visualization_addons import BarGraphModule, OrderBookModule


def make_server(n_agents: int = 200, cont_orders: bool = True) -> ModularServer:
    """Set up the simulation/visualisation server and return it."""
    charts: List[VisualizationElement] = [
        ChartModule([
            {"Label": "Havven Nomins", "Color": "blue"},
            {"Label": "Havven Curits", "Color": "red"},
            {"Label": "Havven Fiat", "Color": "green"}]),

        ChartModule([
            {"Label": "Gini", "Color": "red"},
            {"Label": "Wealth SD", "Color": "blue"}]),

        ChartModule([
            {"Label": "Max Wealth", "Color": "purple"},
            {"Label": "Min Wealth", "Color": "orange"}]),

        ChartModule([
            {"Label": "Profit %", "Color": "red"}]),

        ChartModule([
            {"Label": "Nomins", "Color": "blue"},
            {"Label": "Escrowed Curits", "Color": "red"}]),

        ChartModule([
            {"Label": "Curit Demand", "Color": "red"},
            {"Label": "Curit Supply", "Color": "orange"}]),

        ChartModule([
            {"Label": "Nomin Demand", "Color": "blue"},
            {"Label": "Nomin Supply", "Color": "purple"}]),

        ChartModule([
            {"Label": "Fiat Demand", "Color": "green"},
            {"Label": "Fiat Supply", "Color": "cyan"}]),

        ChartModule([{"Label": "Fee Pool", "Color": "blue"}]),

        ChartModule([{"Label": "Fees Distributed", "Color": "blue"}]),

        BarGraphModule([{"Label": "Wealth"}]),

        OrderBookModule([{"Label": "FiatCurOrderBook"}])
    ]

    n_slider = UserSettableParameter(
        'slider', "Number of agents", n_agents, 2, 2000, 1
    )

    match_checkbox = UserSettableParameter(
        'checkbox', "Continuous order matching", cont_orders
    )

    server = ModularServer(model.Havven, charts, "Havven Model",
                           {"N": n_slider, "match_on_order": match_checkbox})
    return server
