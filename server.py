"""server.py: Functions for setting up the simulation/visualisation server."""


from typing import List
import tornado.web

from visualization.modules import ChartModule, OrderBookModule, WealthModule, PortfolioModule, \
    CurrentOrderModule, CandleStickModule, PastOrdersModule

from visualization.UserParam import UserSettableParameter
from visualization.ModularVisualization import ModularServer
from visualization.VisualizationElement import VisualizationElement
from visualization.CachedServer import CachedModularServer

import settingsloader
import model


def get_vis_elements() -> List[VisualizationElement]:
    ref_colour = "lightgrey"

    return [
        CandleStickModule([
            {"Label": "NominFiatPriceData", "orderbook": "NominFiatOrderBook",
             "AvgColor": "rgba(0,191,255,0.6)", "VolumeColor": "rgba(0,191,255,0.3)"}  # deepskyblue
        ]),

        CandleStickModule([
            {"Label": "HavvenFiatPriceData", "orderbook": "HavvenFiatOrderBook",
             "AvgColor": "rgba(255,0,0,0.6)", "VolumeColor": "rgba(255,0,0,0.3)"}  # red
        ]),

        CandleStickModule([
            {"Label": "HavvenNominPriceData", "orderbook": "HavvenNominOrderBook",
             "AvgColor": "rgba(153,50,204,0.6)", "VolumeColor": "rgba(153,50,204,0.3)"}  # darkorchid
        ]),

        # ChartModule([
        #     {"Label": "Max Wealth", "Color": "purple"},
        #     {"Label": "Min Wealth", "Color": "orange"},
        # ]),

        PortfolioModule([{"Label": "WealthBreakdown"}], fiat_values=False),

        WealthModule([{"Label": "Wealth"}]),

        ChartModule([
            {"Label": "Avg Profit %", "Color": "grey"},
            {"Label": "Bank Profit %", "Color": "blue"},
            {"Label": "Arb Profit %", "Color": "red"},
            {"Label": "Rand Profit %", "Color": "green"},
            {"Label": "NomShort Profit %", "Color": "orchid"},
            {"Label": "EscrowNomShort Profit %", "Color": "darkorchid"},
            {"Label": "NaiveSpec Profit %", "Color": "fuchsia"},
            {"Label": "HavvenSpec Profit %", "Color": "purple"},
            {"Label": "MarketMaker Profit %", "Color": "teal"},
            {"Label": "0", "Color": ref_colour}
        ]),

        CurrentOrderModule([{"Label": "PlayerBidAskVolume"}]),

        PastOrdersModule([{"Label": "TotalMarketVolume"}]),

        ChartModule([
            {"Label": "Havven Demand", "Color": "red"},
            {"Label": "Havven Supply", "Color": "orange"},
        ]),

        ChartModule([
            {"Label": "Nomin Demand", "Color": "deepskyblue"},
            {"Label": "Nomin Supply", "Color": "purple"},
        ]),

        ChartModule([
            {"Label": "Fiat Demand", "Color": "darkgreen"},
            {"Label": "Fiat Supply", "Color": "lightgreen"},
        ]),

        ChartModule([
            {"Label": "Nomins", "Color": "deepskyblue"},
            {"Label": "Escrowed Havvens", "Color": "darkred"},
        ]),

        ChartModule([
            {"Label": "Fee Pool", "Color": "blue"},
            {"Label": "0", "Color": ref_colour}
        ]),

        ChartModule([
            {"Label": "Fees Distributed", "Color": "blue"},
            {"Label": "0", "Color": ref_colour}
        ]),

        ChartModule([
            {"Label": "Havven Nomins", "Color": "deepskyblue"},
            {"Label": "Havven Havvens", "Color": "red"},
            {"Label": "Havven Fiat", "Color": "darkgreen"},
        ]),

        ChartModule([
            {"Label": "Gini", "Color": "navy"},
            {"Label": "0", "Color": ref_colour}
        ]),

        OrderBookModule([{"Label": "NominFiatOrderBook"}]),

        OrderBookModule([{"Label": "HavvenFiatOrderBook"}]),

        OrderBookModule([{"Label": "HavvenNominOrderBook"}])
    ]


def make_server() -> "tornado.web.Application":
    """
    Set up the simulation/visualisation server and return it.

    "Label": "0"/"1" is a workaround to show the graph label where there is only one label
      (the graphs with only one label wont show the label value, and also show multiple
      values at the same time)
    """
    settings = settingsloader.load_settings()

    charts: List[VisualizationElement] = get_vis_elements()

    if settings["Server"]["cached"]:
        server = CachedModularServer(settings, charts, "Havven Model (Alpha)")
        return server
    else:

        n_slider = UserSettableParameter(
            'slider', "Number of agents",
            settings["Model"]["num_agents"], settings["Model"]["num_agents_min"],
            settings["Model"]["num_agents_max"], 1
        )

        ur_slider = UserSettableParameter(
            'slider', "Utilisation Ratio", settings["Model"]["utilisation_ratio_max"], 0.0, 1.0, 0.01
        )

        match_checkbox = UserSettableParameter(
            'checkbox', "Continuous order matching", settings["Model"]["continuous_order_matching"]
        )

        if settings['Model']['random_agents']:
            agent_fraction_selector = UserSettableParameter(
                'agent_fractions', "Agent fraction selector", None
            )
        else:
            # the none value will randomize the data on every model reset
            agent_fraction_selector = UserSettableParameter(
                'agent_fractions', "Agent fraction selector", settings['AgentFractions']
            )

        server = ModularServer(
            settings,
            model.HavvenModel,
            charts,
            "Havven Model (Alpha)",
            {
                "num_agents": n_slider, "utilisation_ratio_max": ur_slider,
                "continuous_order_matching": match_checkbox,
                'agent_fractions': agent_fraction_selector
            }
        )
        return server
