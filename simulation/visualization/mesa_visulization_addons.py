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
    local_includes: List[str] = [
        "visualization/js/chartist.min.js",
        "visualization/js/BarGraphModule.js"
    ]

    def __init__(
            self, series: List[Dict[str, str]], height: int=200,
            width: int=500, data_collector_name: str="datacollector") -> None:
        self.series = series
        self.height = height
        # currently width does nothing, as it stretches the whole page
        self.width = width
        self.data_collector_name = data_collector_name

        self.js_code: str = f"""elements.push(new BarGraphModule(
            \"{series[0]['Label']}\",0,{width},{height}));"""

    def render(self, model: "Havven") -> List[Tuple[str, float]]:
        """
        return the data to be sent to the websocket to be rendered on the page
        """
        data_collector: "DataCollector" = getattr(
            model, self.data_collector_name
        )
        vals: List[Tuple[str, float]] = []

        for s in self.series:
            name = s['Label']
            try:
                # skip the MarketPlayer who is added onto the end as he
                # overshadows the wealth of all the others
                # Note, this should probably be changed later...
                agent_name: List[Callable[float]] = sorted(
                    data_collector.agent_vars["Name"][-1],
                    key=lambda x: x[0]  # sort by ids
                )[:-1]

                agent_func: List[Callable[float]] = sorted(
                    data_collector.agent_vars[name][-1],
                    key=lambda x: x[0]  # sort by ids
                )[:-1]

                for n in range(len(agent_func)):
                    vals.append((
                        agent_name[n][1],
                        agent_func[n][1]()
                    ))
            except Exception as e:
                vals = []
        return vals


class OrderBookModule(VisualizationElement):
    """
    Display a depth graph for orderbooks to show the quantity
    of buy/sell orders for the given market
    """
    package_includes: List[str] = []
    local_includes: List[str] = [
        "visualization/js/chartist.min.js",
        "visualization/js/DepthGraphModule.js"
    ]

    def __init__(
            self, series: List[Dict[str, str]], height: int=300,
            width: int=500, data_collector_name: str="datacollector") -> None:

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

        for s in self.series:
            name: str = s['Label']

            # get the buy and sell orders of the named market and add together
            # the quantities or orders with the same rates

            try:
                orderbook: "OrderBook" = data_collector.model_vars[name][-1]

                for item in orderbook.bids:
                    if len(bids) > 0:
                        if item.price == bids[-1][0]:
                            bids[-1] = (item.price, item.quantity+bids[-1][1])
                        else:
                            bids.append((item.price, item.quantity))
                    else:
                        bids.append((item.price, item.quantity))

                for item in orderbook.asks:
                    if len(asks) > 0:
                        if item.price == asks[-1][0]:
                            asks[-1] = (item.price, item.quantity+asks[-1][1])
                        else:
                            asks.append((item.price, item.quantity))
                    else:
                        asks.append((item.price, item.quantity))

            except:
                pass

        return [bids, asks]
