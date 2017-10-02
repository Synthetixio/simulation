from mesa.visualization.ModularVisualization import VisualizationElement
import numpy as np
import random

class BarGraphModule(VisualizationElement):
    # package_includes = ["Chart.min.js"]
    package_includes = []
    local_includes = ["visualization/css/chartist.min.css", "visualization/js/chartist.min.js", "visualization/js/BarGraphModule.js"]

    def __init__(self, series, num_agents, canvas_height=200, canvas_width=500, data_collector_name="datacollector"):
        self.series = series
        self.num_agents = num_agents
        self.canvas_height = canvas_height
        self.canvas_width = canvas_width
        self.data_collector_name = data_collector_name

        new_element = "new BarGraphModule({}, {}, {})"
        new_element = new_element.format(num_agents,
                                         canvas_width,
                                         canvas_height)
        self.js_code = "elements.push(" + new_element + ");"

    def render(self, model):
        """
        return the data to be sent to the websocket to be rendered on the run page
        """

        data_collector = getattr(model, self.data_collector_name)
        vals = []
        for s in self.series:
            name = s['Label']
            try:
                # skip the MarketPlayer who is added onto the end
                for item in sorted(data_collector.agent_vars[name][-1])[:-1]:
                    vals.append(item[1]())
            except:
                vals = [0 for i in range(self.num_agents)]
        #vals = [random.randint(0,20) for i in range(len(self.bins))]
        #hist = np.histogram(vals, bins=self.bins)[0]
        return vals
