"""
Addons to the mesa visualization system to allow for different graphs and the
viewing of agent variables in a graph format
"""

from mesa.visualization.ModularVisualization import VisualizationElement
import numpy as np
import random

class BarGraphModule(VisualizationElement):
    """
    Displays a simple bar graph of the selected attributes of the agents
    """
    package_includes = []
    local_includes = ["visualization/css/chartist.min.css", "visualization/js/chartist.min.js",
        "visualization/js/BarGraphModule.js"]

    def __init__(self, series: list, height: int=200, width: int=500,
                                        data_collector_name: str="datacollector") -> None:
        self.series = series
        self.height = height
        # currently width does nothing, as it stretches the whole page
        self.width = width
        self.data_collector_name = data_collector_name

        new_element : str = f"new BarGraphModule(\"{series[0]['Label']}\",0, {width}, {height})"
        self.js_code : str = f"elements.push({new_element});"

    def render(self, model: "Havven") -> list:
        """
        return the data to be sent to the websocket to be rendered on the run page
        """
        data_collector = getattr(model, self.data_collector_name)
        vals : "List[Tuple[float,float]]" = []
        for s in self.series:
            name = s['Label']
            try:
                # skip the MarketPlayer who is added onto the end as he overshadows
                # the wealth of all the others
                for item in sorted(data_collector.agent_vars[name][-1])[:-1]:
                    vals.append(item[1]())
            except:
                vals = [0]
        return vals


class OrderBookModule(VisualizationElement):
    """
    Display a depth graph for orderbooks to show the quantity of buy/sell orders
    for the given market
    """
    package_includes = []

    local_includes = ["visualization/css/chartist.min.css", "visualization/js/chartist.min.js",
        "visualization/js/DepthGraphModule.js"]

    def __init__(self, series: list, height: int=300, width: int=500,
                                data_collector_name: str="datacollector") -> None:
        self.series = series
        self.height = height
        # currently width does nothing, as it stretches the whole page
        self.width = width
        self.data_collector_name = data_collector_name

        new_element = f"new DepthGraphModule(\"{series[0]['Label']}\",{width},{height})"
        self.js_code = f"elements.push({new_element});"

    def render(self, model: "Havven") -> list:
        """
        return the data to be sent to the websocket to be rendered on the run page
        """
        self.data_test = [(random.random()*2, random.random()*8) for i in range(100)]
        data_collector = getattr(model, self.data_collector_name)
        vals = []
        for s in self.series:
            name = s['Label']

            # get the buy and sell orders of the named market and add together
            # the quantities or orders with the same rates
            buys = {}
            sells = {}
            try:
                # orderbook = data_collector.model_vars[name][-1]
                # for item in orderbook.buy_orders:
                #     if item.price not in buys:
                #         buys[item.price] = item.quantity
                #     else:
                #         buys[item.price] += item.quantity
                #
                # for item in orderbook.sell_orders:
                #     if item.price not in sells:
                #         sells[item.price] = item.quantity
                #     else:
                #         sells[item.price] += item.quantity
                for item in self.data_test:
                    if item[0] < 1:
                        if item[0] not in buys:
                            buys[item[0]] = item[1]
                        else:
                            buys[item[0]] += item[1]
                    else:
                        if item[0] not in sells:
                            sells[item[0]] = item[1]
                        else:
                            sells[item[0]] += item[1]
            except:
                pass

            buys = sorted(buys.items(), key=lambda x:x[0])
            sells = sorted(sells.items(), key=lambda x:x[0])

        return [buys, sells]
