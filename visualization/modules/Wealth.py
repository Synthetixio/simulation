"""wealth.py: modules for visualising the wealth of agents."""

from typing import List, Tuple, Dict

from mesa.datacollection import DataCollector

from model import Havven

from .BarGraph import BarGraphModule

from orderbook import Bid, Ask

# TODO: make leaving out the last guy optional.


class WealthModule(BarGraphModule):
    def render(self, model: Havven) -> Tuple[List[str], List[str], List[float]]:
        data_collector: "DataCollector" = getattr(
            model, self.data_collector_name
        )

        # short list for names of types, list of actor names, and lists for the wealth breakdowns
        vals: Tuple[List[str], List[str], List[float]] = (["Wealth in fiat"], ["darkgreen"], [1], [], [])

        try:
            agents = sorted(
                data_collector.agent_vars["Agents"][-1],
                key=lambda x: x[0]
            )[:-1]
            for item in agents:
                vals[3].append(item[1].name)
                vals[4].append(float(item[1].wealth()))

        except Exception:
            vals = []
        return vals


PortfolioTuple = Tuple[List[str], List[str], List[int],
                       List[str], List[float], List[float],
                       List[float], List[float], List[float]]


class PortfolioModule(BarGraphModule):
    """
    A bar graph that will show the bars stacked in terms of wealth of different types:
      escrowed_curits, unescrowed_curits, nomins, fiat
    """

    def __init__(self, series: List[Dict[str, str]], height: int = 150,
                 width: int = 500, data_collector_name: str = "datacollector",
                 fiat_values: bool = False) -> None:
        super().__init__(series, height, width, data_collector_name)
        self.fiat_values = fiat_values

    def render(self, model: Havven) -> PortfolioTuple:
        data_collector: "DataCollector" = getattr(
            model, self.data_collector_name
        )

        # vals are [datasets],[colours],[bar #],[playername],[dataset 1],...[dataset n]

        vals: PortfolioTuple = (["Fiat", "Escrowed Curits", "Curits", "Nomins", "Issued Nomins"],
                                ["darkgreen", "darkred", "red", "deepskyblue", "blue"],
                                [1, 1, 1, 1, 1], [], [], [], [], [], [])

        try:
            agents = sorted(
                data_collector.agent_vars["Agents"][-1],
                key=lambda x: x[0]
            )[:-1]

            for item in agents:
                vals[3].append(item[1].name)
                breakdown = item[1].portfolio(self.fiat_values)
                for i in range(len(breakdown)):
                    # assume that issued nomins are last
                    if i+1 == len(breakdown):
                        vals[i + 4].append(-float(breakdown[i]))
                    else:
                        vals[i + 4].append(float(breakdown[i]))


        except Exception:
            vals = []

        return vals


OrderbookValueTuple = Tuple[List[str], List[str], List[int], List[str], List[float], List[float],
                            List[float], List[float], List[float], List[float]]


class CurrentOrderModule(BarGraphModule):
    def render(self, model: Havven) -> OrderbookValueTuple:
        data_collector: "DataCollector" = getattr(
            model, self.data_collector_name
        )

        # vals are [datasets],[colours],[bar #],[playername],[dataset 1],...[dataset n]

        vals: OrderbookValueTuple = (
            ["NomFiatAsk",  "NomFiatBid", "CurFiatAsk", "CurFiatBid", "CurNomAsk", "CurNomBid"],
            ["deepskyblue", "#179473",    "red",        "#8C2E00",    "purple",    "#995266"],
            [1, 1, 2, 2, 3, 3], [], [], [], [], [], [], []
        )

        try:
            agents = sorted(
                data_collector.agent_vars["Agents"][-1],
                key=lambda x: x[0]
            )[:-1]

            for item in agents:
                vals[3].append(item[1].name)
                orders = item[1].orders
                nom_fiat_ask_tot = 0
                nom_fiat_bid_tot = 0
                cur_fiat_ask_tot = 0
                cur_fiat_bid_tot = 0
                nom_cur_ask_tot = 0
                nom_cur_bid_tot = 0

                for order in orders:
                    if order.book.quote == "fiat":
                        if order.book.base == "nomins":
                            # FIAT/NOM
                            if type(order) == Ask:
                                nom_fiat_ask_tot += order.quantity
                            if type(order) == Bid:
                                nom_fiat_bid_tot += order.quantity*order.price
                        if order.book.base == "curits":
                            if type(order) == Ask:
                                cur_fiat_ask_tot += order.quantity
                            if type(order) == Bid:
                                cur_fiat_bid_tot += order.quantity*order.price
                    elif order.book.quote == "nomins":
                        if type(order) == Ask:
                            nom_cur_ask_tot += order.quantity
                        if type(order) == Bid:
                            nom_cur_bid_tot += order.quantity*order.price

                vals[4].append(float(nom_fiat_ask_tot))
                vals[5].append(-float(nom_fiat_bid_tot))
                vals[6].append(float(cur_fiat_ask_tot))
                vals[7].append(-float(cur_fiat_bid_tot))
                vals[8].append(float(nom_cur_ask_tot))
                vals[9].append(-float(nom_cur_bid_tot))

        except Exception:
            vals = []
        return vals


class PastOrdersModule(BarGraphModule):
    def render(self, model: Havven) -> OrderbookValueTuple:
        data_collector: "DataCollector" = getattr(
            model, self.data_collector_name
        )

        # vals are [datasets],[colours],[bar #],[playername],[dataset 1],...[dataset n]

        vals: OrderbookValueTuple = (
            ["NomFiatAsk",  "NomFiatBid", "CurFiatAsk", "CurFiatBid", "CurNomAsk", "CurNomBid"],
            ["deepskyblue", "#179473",    "red",        "#8C2E00",    "purple",    "#995266"],
            [1, 1, 2, 2, 3, 3], [], [], [], [], [], [], []
        )
        try:
            agents = sorted(
                data_collector.agent_vars["Agents"][-1],
                key=lambda x: x[0]
            )[:-1]

            for item in agents:
                vals[3].append(item[1].name)
                trades = item[1].trades
                nom_fiat_ask_tot = 0
                nom_fiat_bid_tot = 0
                cur_fiat_ask_tot = 0
                cur_fiat_bid_tot = 0
                nom_cur_ask_tot = 0
                nom_cur_bid_tot = 0

                for trade in trades:
                    if trade.book.quote == "fiat":
                        if trade.book.base == "nomins":
                            # FIAT/NOM
                            if trade.buyer == item[1]:
                                nom_fiat_ask_tot += trade.quantity
                            elif trade.seller == item[1]:
                                nom_fiat_bid_tot += trade.quantity*trade.price
                        if trade.book.base == "curits":
                            if trade.buyer == item[1]:
                                cur_fiat_ask_tot += trade.quantity
                            elif trade.seller == item[1]:
                                cur_fiat_bid_tot += trade.quantity*trade.price
                    elif trade.book.quote == "nomins":
                        if trade.buyer == item[1]:
                            nom_cur_ask_tot += trade.quantity
                        elif trade.seller == item[1]:
                            nom_cur_bid_tot += trade.quantity*trade.price

                vals[4].append(float(nom_fiat_ask_tot))
                vals[5].append(-float(nom_fiat_bid_tot))
                vals[6].append(float(cur_fiat_ask_tot))
                vals[7].append(-float(cur_fiat_bid_tot))
                vals[8].append(float(nom_cur_ask_tot))
                vals[9].append(-float(nom_cur_bid_tot))

        except Exception:
            vals = []
        return vals
