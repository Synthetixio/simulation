from decimal import Decimal as Dec
from typing import List, Tuple, Dict

from mesa.datacollection import DataCollector

from model import HavvenModel
from core import orderbook as ob
from visualization.visualization_element import VisualizationElement


class CandleStickModule(VisualizationElement):
    """
    Display a depth graph for order books to show the quantity
      of buy/sell orders for the given market
    """
    package_includes: List[str] = ["CandleStickModule.js"]
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
            new CandleStickModule("{group}", "{title}", "{desc}",
                "{series[0]['Label']}",{width},{height},
                "{series[0]['AvgColor']}","{series[0]['VolumeColor']}"
            )
        );"""

    def render(self, model: HavvenModel) -> Tuple[Tuple[float, float, float, float], float, float]:
        """
        return the data to be sent to the websocket to be rendered on the page
        in the format of [[candle data (hi,lo,open,close)], rolling price, volume]
        """
        data_collector: "DataCollector" = getattr(
            model, self.data_collector_name
        )
        price_data: List[Dec] = []
        candle_data: List[Dec] = []
        vol_data: List[Dec] = []

        for s in self.series:  # TODO: not use series, as it should only really be one graph
            name: str = s['orderbook']

            # get the buy and sell orders of the named market and add together
            # the quantities or orders with the same rates

            try:
                order_book: "ob.OrderBook" = data_collector.model_vars[name][-1]
                candle_data = order_book.candle_data[:-1]
                price_data = order_book.price_data[1:]
                vol_data = order_book.volume_data[1:]
            except Exception:
                return (1., 1., 1., 1.), 1., 1.
        # convert decimals to floats
        return (
            (
                float(candle_data[-1][0]),
                float(candle_data[-1][1]),
                float(candle_data[-1][2]),
                float(candle_data[-1][3])
            ),
            float(price_data[-1]),
            float(vol_data[-1])
        )
