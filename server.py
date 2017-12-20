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
import agents


def get_vis_elements() -> List[VisualizationElement]:
    ref_colour = "lightgrey"

    profit_colors = ["blue", "red", "green", "orchid", "darkorchid", "fuchsia", "purple",
              "teal", "darkorange", "darkkaki", "darkgoldenrod", "slategrey", "seagreen"]

    profit_percentage_lines = [
        {"Label": "Avg Profit %", "Color": "grey"},
    ]

    for n, name in enumerate([i for i in agents.player_names if i not in agents.players_to_exclude]):
        profit_percentage_lines.append({"Label": name, "Color": profit_colors[n]})

    return [
        ChartModule(
            profit_percentage_lines,
            desc="Each market player group's profit as a percentage of initial wealth.",
            title="Profitability per Strategy",
            group="Player Aggregate Stats"
        ),

        CandleStickModule(
            [
                {
                    "Label": "NominFiatPriceData", "orderbook": "NominFiatOrderBook",
                    "AvgColor": "rgba(0,191,255,0.6)", "VolumeColor": "rgba(0,191,255,0.3)",  # deepskyblue
                }
            ],
            desc="Candlesticks, rolling price average and volume for the nomin/fiat market.",
            title="Nomin/Fiat Market Price",
            group="Market Prices"
        ),

        CandleStickModule(
            [
                {
                    "Label": "HavvenFiatPriceData", "orderbook": "HavvenFiatOrderBook",
                    "AvgColor": "rgba(255,0,0,0.6)", "VolumeColor": "rgba(255,0,0,0.3)",  # red
                }
            ],
            desc="Candlesticks, rolling price average and volume for the havven/fiat market.",
            title="Havven/Fiat Market Price",
            group="Market Prices"
        ),

        CandleStickModule(
            [
                {
                    "Label": "HavvenNominPriceData", "orderbook": "HavvenNominOrderBook",
                    "AvgColor": "rgba(153,50,204,0.6)", "VolumeColor": "rgba(153,50,204,0.3)",  # darkorchid
                }
            ],
            desc="Candlesticks, rolling price average and volume for the nomin/fiat market.",
            title="Havven/Nomin Market Price",
            group="Market Prices"
        ),
        #
        # # ChartModule([
        # #     {"Label": "Max Wealth", "Color": "purple"},
        # #     {"Label": "Min Wealth", "Color": "orange"},
        # # ]),

        PortfolioModule(
            [{"Label": "WealthBreakdown"}],
            fiat_values=False,
            desc="Player Portfolios",
            title="Wealth Breakdown",
            group="Player Wealth",
        ),

        WealthModule(
            [{"Label": "Wealth"}],
            desc="Individual market player's holdings in terms of fiat.",
            title="Player Net Worth",
            group="Player Wealth"
        ),
        
        ChartModule(
            [{"Label": "Gini", "Color": "navy"}],  # {"Label": "0", "Color": ref_colour}
            desc="Income inequality metric: increases from 0 to 1 as inequality does.",
            title="Gini Coefficient",
            group="Player Wealth"
        ),

        CurrentOrderModule(
            [{"Label": "PlayerBidAskVolume"}],
            desc="Each market player's bids and asks, for each market.",
            title="Outstanding Player Orders",
            group="Player Orders"
        ),

        PastOrdersModule(
            [{"Label": "TotalMarketVolume"}],
            desc="Each market player's bids and asks that were filled, for each market.",
            title="Total Player Order Volume",
            group="Player Orders"
        ),

        ChartModule(
            [
                {"Label": "Havven Demand", "Color": "red"},
                {"Label": "Havven Supply", "Color": "orange"},
            ],
            desc="The aggregate demand and supply of havvens in the markets.",
            title="Havven Order Volume",
            group="Supply and Demand"
        ),

        ChartModule([
            {"Label": "Nomin Demand", "Color": "purple"},
            {"Label": "Nomin Supply", "Color": "deepskyblue"},
        ],
            desc="The aggregate demand and supply of nomins in the markets.",
            title="Nomin Order Volume",
            group="Supply and Demand"
        ),

        ChartModule([
            {"Label": "Fiat Demand", "Color": "darkgreen"},
            {"Label": "Fiat Supply", "Color": "lightgreen"},
        ],
            desc="The aggregate demand and supply of fiat in the markets.",
            title="Fiat Order Volume",
            group="Supply and Demand"
        ),

        ChartModule([
            {"Label": "Nomins", "Color": "deepskyblue"},
            {"Label": "Escrowed Havvens", "Color": "darkred"},
        ],
            desc="The total number of nomins and escrowed havvens for all market players.",
            title="Nomins to Escrowed Havvens",
            group="Issuance"
        ),

        ChartModule([
            {"Label": "Fee Pool", "Color": "blue"},
        ],
            desc="The amount of fees collected by the system, that haven't yet been distributed.",
            title="Collected Fees",
            group="Fees"
        ),

        ChartModule([
            {"Label": "Fees Distributed", "Color": "blue"},
        ],
            desc="Total amount of fees that have been distributed by the system.",
            title="Distributed Fees",
            group="Fees"
        ),
        #
        # ChartModule([
        #     {"Label": "Havven Nomins", "Color": "deepskyblue"},
        #     {"Label": "Havven Havvens", "Color": "red"},
        #     {"Label": "Havven Fiat", "Color": "darkgreen"},
        # ]),
        #

        OrderBookModule(
            [{"Label": "NominFiatOrderBook"}],
            desc="The nomin/fiat market order book (tallied bid/ask volume by price).",
            title="Nomin/Fiat Order Book",
            group="Order Books"
        ),

        OrderBookModule(
            [{"Label": "HavvenFiatOrderBook"}],
            desc="The havven/fiat market order book (tallied bid/ask volume by price).",
            title="Havven/Fiat Order Book",
            group="Order Books"
        ),

        OrderBookModule(
            [{"Label": "HavvenNominOrderBook"}],
            desc="The Havven/Nomin market order book (tallied bid/ask volume by price).",
            title="Havven/Nomin Order Book",
            group="Order Books"
        )
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
        print("Running cached data server...")

        server = CachedModularServer(settings, charts, "Havven Model (Alpha)")

    else:
        print("Running model server...")

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
