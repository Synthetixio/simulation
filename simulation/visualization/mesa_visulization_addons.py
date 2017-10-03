from mesa.visualization.ModularVisualization import VisualizationElement
import numpy as np
import random

class BarGraphModule(VisualizationElement):
    """
    Displays a simple bar graph of the selected attributes of the agents
    """
    # package_includes = ["Chart.min.js"]
    package_includes = []
    local_includes = ["visualization/css/chartist.min.css", "visualization/js/chartist.min.js",
        "visualization/js/chartist-plugin-tooltip.js", "visualization/js/BarGraphModule.js"]

    def __init__(self, series, num_agents, height=200, width=500, data_collector_name="datacollector"):
        self.series = series
        self.num_agents = num_agents
        self.height = height

        # currently width does nothing, as it stretches the whole page
        self.width = width
        self.data_collector_name = data_collector_name

        new_element = f"new BarGraphModule(\"{series[0]['Label']}\",{num_agents}, {width}, {height})"

        self.js_code = f"elements.push({new_element});"

    def render(self, model):
        """
        return the data to be sent to the websocket to be rendered on the run page
        """
        data_collector = getattr(model, self.data_collector_name)
        vals = []
        for s in self.series:
            name = s['Label']
            try:
                # skip the MarketPlayer who is added onto the end as he overshadows all the others
                for item in sorted(data_collector.agent_vars[name][-1])[:-1]:
                    vals.append(item[1]())
            except:
                vals = [0 for i in range(self.num_agents)]
        return vals


class OrderBookModule(VisualizationElement):

    package_includes = []

    local_includes = ["visualization/css/chartist.min.css", "visualization/js/chartist.min.js",
        "visualization/js/chartist-plugin-tooltip.js", "visualization/js/DepthGraphModule.js"]

    def __init__(self, series, height=300, width=500, data_collector_name="datacollector"):
        self.series = series
        self.height = height
        # currently width does nothing, as it stretches the whole page
        self.width = width
        self.data_collector_name = data_collector_name

        new_element = f"new DepthGraphModule(\"{series[0]['Label']}\",{width},{height})"
        self.js_code = f"elements.push({new_element});"

    def render(self, model):
        """
        return the data to be sent to the websocket to be rendered on the run page
        """
        data_collector = getattr(model, self.data_collector_name)
        vals = []
        for s in self.series:
            name = s['Label']

            # get the buy and sell orders of the named market and add together
            # the quantities or orders with the same rates
            buys = {}
            sells = {}
            try:
                orderbook = data_collector.model_vars[name][-1]
                for item in orderbook.buy_orders:
                    if item.price not in buys:
                        buys[item.price] = item.quantity
                    else:
                        buys[item.price] += item.quantity

                for item in orderbook.sell_orders:
                    if item.price not in sells:
                        sells[item.price] = item.quantity
                    else:
                        sells[item.price] += item.quantity
            except:
                pass
            buys = sorted(buys.items(), key=lambda x:x[0])
            sells = sorted(sells.items(), key=lambda x:x[0])

        # TODO: the graph is receiving data in the form (rate, quant) but the
        #       quantity isn't accumulated over the multiple rates
        #       that needs to be done either here or in the js

        return [buys, sells]
