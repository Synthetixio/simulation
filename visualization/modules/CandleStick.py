from typing import List, Tuple, Dict
from decimal import Decimal as Dec

from mesa.datacollection import DataCollector
from visualization.ModularVisualization import VisualizationElement

from model import Havven
import orderbook as ob


class CandleStickModule(VisualizationElement):
    """
    Display a depth graph for order books to show the quantity
      of buy/sell orders for the given market
    """
    package_includes: List[str] = ["Chart.Financial.js", "CandleStickModule.js"]
    local_includes: List[str] = []

    def __init__(
            self, series: List[Dict[str, str]], height: int = 150,
            width: int = 500, data_collector_name: str = "datacollector") -> None:

        self.series = series
        self.height = height
        # currently width does nothing, as it stretches the whole page
        self.width = width
        self.data_collector_name = data_collector_name

        self.js_code = f"""elements.push(
            new CandleStickModule(\"{series[0]['Label']}\",{width},{height})
        );"""

    def render(self, model: Havven) -> List[List[float]]:
        """
        return the data to be sent to the websocket to be rendered on the page
        """
        data_collector: "DataCollector" = getattr(
            model, self.data_collector_name
        )
        price = 1.0
        data: List[Dec] = []

        for s in self.series:  # TODO: not use series, as it should only really be one graph
            name: str = s['orderbook']

            # get the buy and sell orders of the named market and add together
            # the quantities or orders with the same rates

            try:
                order_book: "ob.OrderBook" = data_collector.model_vars[name][-1]
                data = order_book.candle_data
            except Exception:
                data = []

        # convert decimals to floats
        return [list(map(lambda x: float(x) if x else -1, i)) for i in data]
