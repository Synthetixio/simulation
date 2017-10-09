"""
Addons to the mesa visualization system to allow for different graphs and the
viewing of agent variables in a graph format
"""


from mesa.visualization.ModularVisualization import VisualizationElement

import numpy as np
import random

from typing import List, Tuple, Dict, Callable

class BarGraphModule(VisualizationElement):
    """
    Displays a simple bar graph of the selected attributes of the agents
    """
    package_includes: List[str] = []
    local_includes: List[str] = ["visualization/css/chartist.min.css", "visualization/js/chartist.min.js",
        "visualization/js/BarGraphModule.js"]

    def __init__(self, series: List[Dict[str, str]], height: int=200, width: int=500,
                                        data_collector_name: str="datacollector") -> None:
        self.series = series
        self.height = height
        # currently width does nothing, as it stretches the whole page
        self.width = width
        self.data_collector_name = data_collector_name

        new_element: str = f"new BarGraphModule(\"{series[0]['Label']}\",0, {width}, {height})"
        self.js_code: str = f"elements.push({new_element});"

    def render(self, model: "Havven") -> List[float]:
        """
        return the data to be sent to the websocket to be rendered on the run page
        """
        data_collector: "DataCollector" = getattr(model, self.data_collector_name)
        vals : List[float] = []
        for s in self.series:
            name = s['Label']
            try:
                # skip the MarketPlayer who is added onto the end as he overshadows
                # the wealth of all the others
                agents: List[Callable[float]] = sorted(data_collector.agent_vars[name][-1])[:-1]
                for item in agents:
                    vals.append(item[1]())
            except:
                vals = [0]
        return vals


class OrderBookModule(VisualizationElement):
    """
    Display a depth graph for orderbooks to show the quantity of buy/sell orders
    for the given market
    """
    package_includes: List[str] = []
    local_includes: List[str] = ["visualization/css/chartist.min.css", "visualization/js/chartist.min.js",
        "visualization/js/DepthGraphModule.js"]

    def __init__(self, series: List[Dict[str, str]], height: int=300, width: int=500,
                                data_collector_name: str="datacollector") -> None:
        self.series = series
        self.height = height
        # currently width does nothing, as it stretches the whole page
        self.width = width
        self.data_collector_name = data_collector_name

        new_element: str = f"new DepthGraphModule(\"{series[0]['Label']}\",{width},{height})"
        self.js_code = f"elements.push({new_element});"

    def render(self, model: "Havven") -> List[List[Tuple[float,float]]]:
        """
        return the data to be sent to the websocket to be rendered on the run page
        """
        data_collector: "DataCollector" = getattr(model, self.data_collector_name)

        for s in self.series:
            name: str = s['Label']

            # get the buy and sell orders of the named market and add together
            # the quantities or orders with the same rates
            bid_dict: Dict[float,float] = {}
            ask_dict: Dict[float,float] = {}
            try:
                orderbook: "OrderBook" = data_collector.model_vars[name][-1]
                for item in orderbook.bids:
                    if item.price not in bid_dict:
                        bid_dict[item.price] = item.quantity
                    else:
                        bid_dict[item.price] += item.quantity

                for item in orderbook.asks:
                    if item.price not in ask_dict:
                        ask_dict[item.price] = item.quantity
                    else:
                        ask_dict[item.price] += item.quantity
                # for item in self.data_test:
                #     if item[0] < 1:
                #         if item[0] not in bid_dict:
                #             bid_dict[item[0]] = item[1]
                #         else:
                #             bid_dict[item[0]] += item[1]
                #     else:
                #         if item[0] not in ask_dict:
                #             ask_dict[item[0]] = item[1]
                #         else:
                #             ask_dict[item[0]] += item[1]
            except:
                pass

            bids: List[Tuple[float,float]] = sorted(bid_dict.items(), key=lambda x:x[0])
            asks: List[Tuple[float,float]] = sorted(ask_dict.items(), key=lambda x:x[0])
        print([bids, asks])
        return [bids, asks]
