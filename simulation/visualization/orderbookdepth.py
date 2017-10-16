from typing import List, Tuple, Dict
from decimal import Decimal

from mesa.datacollection import DataCollector
from mesa.visualization.ModularVisualization import VisualizationElement

from model import Havven
import orderbook as ob


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

    def render(self, model: Havven) -> List[List[Tuple[float, float]]]:
        """
        return the data to be sent to the websocket to be rendered on the page
        """
        data_collector: "DataCollector" = getattr(
            model, self.data_collector_name
        )

        bids: List[Tuple["Decimal", "Decimal"]] = []
        asks: List[Tuple["Decimal", "Decimal"]] = []

        for s in self.series:  # TODO: not use series, as it should only really be one graph
            name: str = s['Label']

            # get the buy and sell orders of the named market and add together
            # the quantities or orders with the same rates

            try:
                order_book: "ob.OrderBook" = data_collector.model_vars[name][-1]
                for item in order_book.bids:
                    price = round(item.price, model.manager.currency_precision)
                    if len(bids) > 0:
                        if price == bids[-1][0]:
                            bids[-1] = (price, item.quantity + bids[-1][1])
                        else:
                            bids.append((price, item.quantity))
                    else:
                        bids.append((price, item.quantity))

                for item in order_book.asks:
                    price = round(item.price, model.manager.currency_precision)
                    if len(asks) > 0:
                        if price == asks[-1][0]:
                            asks[-1] = (price, item.quantity + asks[-1][1])
                        else:
                            asks.append((price, item.quantity))
                    else:
                        asks.append((price, item.quantity))

            except Exception:
                bids = []
                asks = []

        # convert decimals to floats
        return [[(float(i[0]), float(i[1])) for i in bids], [(float(i[0]), float(i[1])) for i in asks]]
