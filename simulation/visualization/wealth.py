"""wealth.py: modules for visualising the wealth of agents."""

from typing import List, Tuple, Dict

from mesa.datacollection import DataCollector

from model import Havven

from .bargraph import BarGraphModule

# TODO: make leaving out the last guy optional.

class WealthModule(BarGraphModule):
    def render(self, model: Havven) -> Tuple[List[str], List[str], List[float]]:
        data_collector: "DataCollector" = getattr(
            model, self.data_collector_name
        )

        # short list for names of types, list of actor names, and lists for the wealth breakdowns
        vals: Tuple[List[str], List[str], List[float]] = ([], [], [])

        try:
            agents = sorted(
                data_collector.agent_vars["Agents"][-1],
                key=lambda x: x[0]
            )[:-1]

            for item in agents:
                vals[1].append(item[1].name)
                vals[2].append(item[1].wealth())

        except Exception:
            vals = []
        return vals



WealthBreakdown = Tuple[List[str], List[str],
                        List[float], List[float],
                        List[float], List[float]]


class WealthBreakdownModule(BarGraphModule):
    """
    A bar graph that will show the bars stacked in terms of wealth of different types:
      escrowed_curits, unescrowed_curits, nomins, fiat
    """

    def __init__(self, series: List[Dict[str, str]], height: int = 200,
                 width: int = 500, data_collector_name: str = "datacollector",
                 absolute: bool = False) -> None:
        super().__init__(series, height, width, data_collector_name)
        self.absolute = absolute

    def render(self, model: Havven) -> WealthBreakdown:
        data_collector: "DataCollector" = getattr(
            model, self.data_collector_name
        )

        # short list for names of types, list of actor names, and lists for the wealth breakdowns
        vals: WealthBreakdown = (["Curits", "Escrowed Curits", "Nomins", "Fiat", "Issued Nomins"],
                                 [], [], [], [], [], [])

        try:
            agents = sorted(
                data_collector.agent_vars["Agents"][-1],
                key=lambda x: x[0]
            )[:-1]

            for item in agents:
                vals[1].append(item[1].name)
                breakdown = item[1].wealth_breakdown(self.absolute)
                for i in range(len(breakdown)):
                    vals[i + 2].append(breakdown[i])

        except Exception:
            vals = []

        return vals

