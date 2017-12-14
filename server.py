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
        CandleStickModule(
            [
                {
                    "Label": "NominFiatPriceData", "orderbook": "NominFiatOrderBook",
                    "AvgColor": "rgba(0,191,255,0.6)", "VolumeColor": "rgba(0,191,255,0.3)",  # deepskyblue
                }
            ],
            desc="Candlesticks, rolling price average and volume for the Nomin/Fiat market",
            title="Nomin/Fiat Market Price data",
            group="Market Prices"
        ),

        CandleStickModule(
            [
                {
                    "Label": "HavvenFiatPriceData", "orderbook": "HavvenFiatOrderBook",
                    "AvgColor": "rgba(255,0,0,0.6)", "VolumeColor": "rgba(255,0,0,0.3)",  # red
                }
            ],
            desc="Candlesticks, rolling price average and volume for the Havven/Fiat market",
            title="Havven/Fiat Market Price data",
            group="Market Prices"
        ),

        CandleStickModule(
            [
                {
                    "Label": "HavvenNominPriceData", "orderbook": "HavvenNominOrderBook",
                    "AvgColor": "rgba(153,50,204,0.6)", "VolumeColor": "rgba(153,50,204,0.3)",  # darkorchid
                }
            ],
            desc="Candlesticks, rolling price average and volume for the Nomin / Fiat market",
            title="Havven/Nomin Market Price data",
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
            desc="Individual market player's holdings",
            title="Wealth Breakdown",
            group="Player Wealth",
        ),

        WealthModule(
            [{"Label": "Wealth"}],
            desc="Individual market player's holdings in terms of Fiat",
            title="Total wealth in FIAT",
            group="Player Wealth"
        ),

        ChartModule(
            [
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
            ],
            desc="Each market player group's profit in a percentage compared to initial wealth",
            title="Player's profit %",
            group="Player Type Aggregates"
        ),

        CurrentOrderModule(
            [{"Label": "PlayerBidAskVolume"}],
            desc="Each market player's Bids and asks, for each market",
            title="Player's Current Bid Ask Volume",
            group="Player Market Usage"
        ),

        PastOrdersModule(
            [{"Label": "TotalMarketVolume"}],
            desc="Each market player's Bids and asks that were filled, for each market",
            title="Player's Total Bid Ask Volume",
            group="Player Market Usage"
        ),

        ChartModule(
            [
                {"Label": "Havven Demand", "Color": "red"},
                {"Label": "Havven Supply", "Color": "orange"},
            ],
            desc="The total demand and supply of Havvens on the markets",
            title="Havven Usage",
            group="Total Currency Demand"
        ),

        ChartModule([
            {"Label": "Nomin Demand", "Color": "deepskyblue"},
            {"Label": "Nomin Supply", "Color": "purple"},
        ],
            desc="The total demand and supply of Nomins on the markets",
            title="Nomin Usage",
            group="Total Currency Demand"
        ),

        ChartModule([
            {"Label": "Fiat Demand", "Color": "darkgreen"},
            {"Label": "Fiat Supply", "Color": "lightgreen"},
        ],
            desc="The total demand and supply of Fiat on the markets",
            title="Fiat Usage",
            group="Total Currency Demand"
        ),

        ChartModule([
            {"Label": "Nomins", "Color": "deepskyblue"},
            {"Label": "Escrowed Havvens", "Color": "darkred"},
        ],
            desc="The total number of nomins and Escrowed Havvens for all market players",
            title="Nomins to Escrowed Havvens",
            group="Issuance Statistics"
        ),

        ChartModule([
            {"Label": "Fee Pool", "Color": "blue"},
            {"Label": "0", "Color": ref_colour}
        ],
            desc="The amount of fees collected by the system, that haven't been distributed",
            title="Collected Fees",
            group="Fees"
        ),

        ChartModule([
            {"Label": "Fees Distributed", "Color": "blue"},
            {"Label": "0", "Color": ref_colour}
        ],
            desc="Total amount of fees that have been distributed by the system",
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
        # ChartModule([
        #     {"Label": "Gini", "Color": "navy"},
        #     {"Label": "0", "Color": ref_colour}
        # ]),

        OrderBookModule(
            [{"Label": "NominFiatOrderBook"}],
            desc="The Nomin/Fiat market orderbook (tallied bid/ask volume by price)",
            title="Nomin/Fiat Orderbook",
            group="Orderbooks"
        ),

        OrderBookModule(
            [{"Label": "HavvenFiatOrderBook"}],
            desc="The Havven/Fiat market orderbook (tallied bid/ask volume by price)",
            title="Havven/Fiat Orderbook",
            group="Orderbooks"
        ),

        OrderBookModule(
            [{"Label": "HavvenNominOrderBook"}],
            desc="The Havven/Nomin market orderbook (tallied bid/ask volume by price)",
            title="Havven/Nomin Orderbook",
            group="Orderbooks"
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
        print("Running Cached data server...")

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
