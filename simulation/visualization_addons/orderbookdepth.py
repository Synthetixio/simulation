from typing import List, Tuple, Dict

from mesa.datacollection import DataCollector
from mesa.visualization.ModularVisualization import VisualizationElement

import model
import orderbook as ob


class OrderBookModule(VisualizationElement):
    """
    Display a depth graph for orderbooks to show the quantity
    of buy/sell orders for the given market
    """
    package_includes: List[str] = []
    local_includes: List[str] = [
        "visualization_addons/js/chartist.min.js",
        "visualization_addons/js/DepthGraphModule.js"
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

    def render(self, model: "model.Havven") -> List[List[Tuple[float, float]]]:
        """
        return the data to be sent to the websocket to be rendered on the page
        """
        data_collector: "DataCollector" = getattr(
            model, self.data_collector_name
        )

        bids: List[Tuple[float, float]] = []
        asks: List[Tuple[float, float]] = []

        for s in self.series: # TODO: not use series, as it should only really be one graph
            name: str = s['Label']

            # get the buy and sell orders of the named market and add together
            # the quantities or orders with the same rates

            try:
                orderbook: "ob.OrderBook" = data_collector.model_vars[name][-1]

                for item in orderbook.bids:
                    if len(bids) > 0:
                        if item.price == bids[-1][0]:
                            bids[-1] = (item.price, item.quantity + bids[-1][1])
                        else:
                            bids.append((item.price, item.quantity))
                    else:
                        bids.append((item.price, item.quantity))

                for item in orderbook.asks:
                    if len(asks) > 0:
                        if item.price == asks[-1][0]:
                            asks[-1] = (item.price, item.quantity + asks[-1][1])
                        else:
                            asks.append((item.price, item.quantity))
                    else:
                        asks.append((item.price, item.quantity))

            except Exception as e:
                bids = []
                asks = []

        return [bids, asks]
