from typing import List, Tuple, Dict, Callable

from mesa.datacollection import DataCollector
from mesa.visualization.ModularVisualization import VisualizationElement

import model

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
            self, series: List[Dict[str, str]], height: int = 200,
            width: int = 500, data_collector_name: str = "datacollector") -> None:
        self.series = series
        self.height = height
        # currently width does nothing, as it stretches the whole page
        self.width = width
        self.data_collector_name = data_collector_name

        self.js_code: str = f"""elements.push(new BarGraphModule(
            \"{series[0]['Label']}\",0,{width},{height}));"""

    def render(self, model: "model.Havven") -> List[Tuple[str, float]]:
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
