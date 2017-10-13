"""
Addons to the mesa visualization system to allow for different graphs and the
viewing of agent variables in a graph format
"""

import numpy as np
import random
from typing import List, Tuple, Dict, Callable

from mesa.datacollection import DataCollector
from mesa.visualization.ModularVisualization import VisualizationElement

from model import Havven
import orderbook as ob


class BarGraphModule(VisualizationElement):
    """
    Displays a simple bar graph of the selected attributes of the agents
    """
    package_includes: List[str] = []
    local_includes: List[str] = [
        "visualization/js/chartist.min.js",
        "visualization/js/BarGraphModule.js"
    ]

    def __init__(self, series: List[Dict[str, str]], height: int = 200,
                 width: int = 500, data_collector_name: str = "datacollector") -> None:
        self.series = series
        self.height = height
        # currently width does nothing, as it stretches the whole page
        self.width = width
        self.data_collector_name = data_collector_name

        # the code to be rendered on the page, last bool is whether it will be a stack graph
        self.js_code: str = f"""elements.push(new BarGraphModule(
            \"{series[0]['Label']}\",0,{width},{height},false));"""

    def render(self, model: "Havven") -> List[Tuple[str, float]]:
        """
        return the data to be sent to the websocket to be rendered on the page
        """
        data_collector: "DataCollector" = getattr(
            model, self.data_collector_name
        )
        vals: List[Tuple[str, float]] = []

        return vals


class TotalWealthModule(BarGraphModule):
    def render(self, model: "Havven") -> Tuple[List[str], List[str], List[float]]:
        data_collector: "DataCollector" = getattr(
            model, self.data_collector_name
        )

        # short list for names of types, list of actor names, and lists for the wealth breakdowns
        vals: Tuple[List[str], List[str], List[float]] = ([], [], [])

        try:
            agents = sorted(
                data_collector.agent_vars["Agents"][-1],
                key=lambda x: x[0]
            )[:-1]

            for item in agents:
                vals[1].append(item[1].name)
                vals[2].append(item[1].wealth())

        except Exception:
            vals = []
        return vals



wealth_breakdown_type = Tuple[List[str], List[str],
                              List[float], List[float],
                              List[float], List[float]]


class WealthBreakdownModule(BarGraphModule):
    """
    A bar graph that will show the bars stacked in terms of wealth of different types:
      escrowed_curits, unescrowed_curits, nomins, fiat
    """

    def render(self, model: "Havven") -> wealth_breakdown_type:
        data_collector: "DataCollector" = getattr(
            model, self.data_collector_name
        )

        # short list for names of types, list of actor names, and lists for the wealth breakdowns
        vals: wealth_breakdown_type = (["Curits", "Escrowed Curits", "Nomins", "Fiat", "Issued Nomins"],
                                       [], [], [], [], [], [])

        try:
            agents = sorted(
                data_collector.agent_vars["Agents"][-1],
                key=lambda x: x[0]
            )[:-1]

            for item in agents:
                vals[1].append(item[1].name)
                breakdown = item[1].wealth_breakdown()
                for i in range(len(breakdown)):
                    vals[i + 2].append(breakdown[i])

        except Exception:
            vals = []

        return vals


class OrderBookModule(VisualizationElement):
    """
    Display a depth graph for order books to show the quantity
      of buy/sell orders for the given market
    """
    package_includes: List[str] = []
    local_includes: List[str] = [
        "visualization/js/chartist.min.js",
        "visualization/js/DepthGraphModule.js"
    ]

    def __init__(
            self, series: List[Dict[str, str]], height: int = 300,
            width: int = 500, data_collector_name: str = "datacollector") -> None:

        self.series = series
        self.height = height
        # currently width does nothing, as it stretches the whole page
        self.width = width
        self.data_collector_name = data_collector_name

        self.js_code = f"""elements.push(
            new DepthGraphModule(\"{series[0]['Label']}\",{width},{height})
        );"""

    def render(self, model: "Havven") -> List[List[Tuple[float, float]]]:
        """
        return the data to be sent to the websocket to be rendered on the page
        """
        data_collector: "DataCollector" = getattr(
            model, self.data_collector_name
        )

        bids: List[Tuple[float, float]] = []
        asks: List[Tuple[float, float]] = []

        for s in self.series:  # TODO: not use series, as it should only really be one graph
            name: str = s['Label']

            # get the buy and sell orders of the named market and add together
            # the quantities or orders with the same rates

            try:
                order_book: "ob.OrderBook" = data_collector.model_vars[name][-1]

                for item in order_book.bids:
                    if len(bids) > 0:
                        if item.price == bids[-1][0]:
                            bids[-1] = (item.price, item.quantity + bids[-1][1])
                        else:
                            bids.append((item.price, item.quantity))
                    else:
                        bids.append((item.price, item.quantity))

                for item in order_book.asks:
                    if len(asks) > 0:
                        if item.price == asks[-1][0]:
                            asks[-1] = (item.price, item.quantity + asks[-1][1])
                        else:
                            asks.append((item.price, item.quantity))
                    else:
                        asks.append((item.price, item.quantity))

            except Exception:
                bids = []
                asks = []

        return [bids, asks]
