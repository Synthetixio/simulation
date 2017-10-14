"""bargraph.py: a module for rendering a histogram-style bar chart."""

from typing import List, Tuple, Dict

from mesa.datacollection import DataCollector
from mesa.visualization.ModularVisualization import VisualizationElement

from model import Havven


class BarGraphModule(VisualizationElement):
    """
    Displays a simple bar graph of the selected attributes of the agents
    """
    package_includes: List[str] = []
    local_includes: List[str] = [
        "visualization/js/chartist.min.js",
        "visualization/js/BarGraphModule.js"
    ]

    def __init__(self, series: List[Dict[str, str]], height: int = 200,
                 width: int = 500, data_collector_name: str = "datacollector") -> None:
        self.series = series
        self.height = height
        # currently width does nothing, as it stretches the whole page
        self.width = width
        self.data_collector_name = data_collector_name

        # the code to be rendered on the page, last bool is whether it will be a stack graph
        self.js_code: str = f"""elements.push(new BarGraphModule(
            \"{series[0]['Label']}\",0,{width},{height},false));"""

    def render(self, model: Havven) -> List[Tuple[str, float]]:
        """
        return the data to be sent to the websocket to be rendered on the page
        """
        data_collector: "DataCollector" = getattr(
            model, self.data_collector_name
        )
        vals: List[Tuple[str, float]] = []

        return vals
