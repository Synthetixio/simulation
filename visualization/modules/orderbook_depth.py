from decimal import Decimal as Dec
from typing import List, Tuple, Dict

from mesa.datacollection import DataCollector

from core import orderbook as ob
from core.model import HavvenModel
from visualization.visualization_element import VisualizationElement


class OrderBookModule(VisualizationElement):
    """
    Display a depth graph for order books to show the quantity
      of buy/sell orders for the given market
    """
    package_includes: List[str] = ["DepthGraphModule.js"]
    local_includes: List[str] = []

    def __init__(
            self, series: List[Dict[str, str]], height: int = 150,
            width: int = 500, data_collector_name: str = "datacollector",
            desc: str = "", title: str = "", group: str = "") -> None:

        self.series = series
        self.height = height
        # currently width does nothing, as it stretches the whole page
        self.width = width
        self.data_collector_name = data_collector_name

        self.js_code = f"""elements.push(
            new DepthGraphModule("{group}", "{title}", "{desc}", "{series[0]['Label']}",{width},{height})
        );"""

    def render(self, model: HavvenModel) -> List[List[Tuple[float, float]]]:
        """
        return the data to be sent to the websocket to be rendered on the page
        """
        data_collector: "DataCollector" = getattr(
            model, self.data_collector_name
        )
        price = 1.0
        bids: List[Tuple[Dec, Dec]] = []
        asks: List[Tuple[Dec, Dec]] = []

        for s in self.series:  # TODO: not use series, as it should only really be one graph
            name: str = s['Label']

            # get the buy and sell orders of the named market and add together
            # the quantities or orders with the same rates

            try:
                order_book: "ob.OrderBook" = data_collector.model_vars[name][-1]
                price = order_book.price
                bids = order_book.bid_price_buckets.items()
                asks = order_book.ask_price_buckets.items()
            except Exception:
                bids = []
                asks = []

        # convert decimals to floats

        return [float(price), [(float(i[0]), float(i[1])) for i in bids], [(float(i[0]), float(i[1])) for i in asks]]
