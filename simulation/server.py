"""server.py: Functions for setting up the simulation/visualisation server."""

from typing import List

from mesa.visualization.modules import ChartModule
from mesa.visualization.UserParam import UserSettableParameter
from mesa.visualization.ModularVisualization import ModularServer, VisualizationElement

import model
from visualization.mesa_visualization_addons import BarGraphModule, OrderBookModule


def make_server(n_agents: int = 50, ur: float = 0.2,
                cont_orders: bool = True) -> ModularServer:
    """
    Set up the simulation/visualisation server and return it.

    "Label": "" is a workaround to show the graph label where there is only one label
      (the graphs with only one label wont show the label value, and also show multiple
      values at the same time)
    """
    charts: List[VisualizationElement] = [
        ChartModule([
            {"Label": "1", "Color": "grey"},
            {"Label": "Nomin Price", "Color": "blue"},
            {"Label": "Nomin Ask", "Color": "blue"},
            {"Label": "Nomin Bid", "Color": "blue"}]),

        ChartModule([
            {"Label": "1", "Color": "grey"},
            {"Label": "Curit Price", "Color": "orange"},
            {"Label": "Curit Ask", "Color": "orange"},
            {"Label": "Curit Bid", "Color": "orange"}]),

        ChartModule([
            {"Label": "1", "Color": "grey"},
            {"Label": "Curit/Nomin Price", "Color": "purple"},
            {"Label": "Curit/Nomin Ask", "Color": "purple"},
            {"Label": "Curit/Nomin Bid", "Color": "purple"}]),

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
            {"Label": "0", "Color": "grey"},
            {"Label": "Avg Profit %", "Color": "grey"},
            {"Label": "Bank Profit %", "Color": "blue"},
            {"Label": "Arb Profit %", "Color": "red"},
            {"Label": "Rand Profit %", "Color": "green"}]),

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

        ChartModule([
            {"Label": "0", "Color": "grey"},
            {"Label": "Fee Pool", "Color": "blue"}]),

        ChartModule([
            {"Label": "0", "Color": "grey"},
            {"Label": "Fees Distributed", "Color": "blue"}]),

        BarGraphModule([{"Label": "Wealth"}]),

        OrderBookModule([{"Label": "NomFiatOrderBook"}]),

        OrderBookModule([{"Label": "CurFiatOrderBook"}]),

        OrderBookModule([{"Label": "CurNomOrderBook"}])
    ]

    n_slider = UserSettableParameter(
        'slider', "Number of agents", n_agents, 2, 2000, 1
    )

    ur_slider = UserSettableParameter(
        'slider', "Utilisation Ratio", ur, 0.0, 1.0, 0.01
    )

    match_checkbox = UserSettableParameter(
        'checkbox', "Continuous order matching", cont_orders
    )

    server = ModularServer(model.Havven, charts, "Havven Model",
                           {"num_agents": n_slider, "utilisation_ratio_max": ur_slider,
                            "match_on_order": match_checkbox})
    return server
