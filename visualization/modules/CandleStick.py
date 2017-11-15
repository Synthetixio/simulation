from typing import List, Tuple, Dict
from decimal import Decimal as Dec

from mesa.datacollection import DataCollector
from visualization.VisualizationElement import VisualizationElement

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
            new CandleStickModule(
                \"{series[0]['Label']}\",{width},{height},
                "{series[0]['AvgColor']}","{series[0]['VolumeColor']}"
            )
        );"""

        self.chart_length = 85

    def render(self, model: Havven) -> Tuple[List[float], List[float], List[float], List[float]]:
        """
        return the data to be sent to the websocket to be rendered on the page
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
                candle_data = []
                price_data = []
                vol_data = []

        old_len = len(candle_data)
        if len(candle_data) > self.chart_length:
            candle_data = candle_data[-self.chart_length:]
            price_data = price_data[-self.chart_length:]
            vol_data = vol_data[-self.chart_length:]

        # convert decimals to floats
        return (
            list(map(lambda x: (float(x[0]), float(x[1]), float(x[2]), float(x[3])) if x[1] else -1.0, candle_data)),
            [float(i) for i in price_data],
            [float(i) for i in vol_data],
            [i for i in range(old_len-len(vol_data), old_len+1)]
        )
