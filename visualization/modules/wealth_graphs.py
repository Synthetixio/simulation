"""wealth.py: modules for visualising the wealth of agents."""

from typing import List, Tuple, Dict

from mesa.datacollection import DataCollector

from model import HavvenModel
from core.orderbook import Bid, Ask
from .bargraph import BarGraphModule


# TODO: make leaving out the last guy optional.


class WealthModule(BarGraphModule):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ensure the data for agent names/colours only appears in the first tick
        self.sent_data = False

    def render(self, model: HavvenModel) -> Tuple[List[str], List[str], List[float]]:
        data_collector: "DataCollector" = getattr(
            model, self.data_collector_name
        )

        if len(data_collector.agent_vars["Agents"]) <= 1:
            self.sent_data = False

        if not self.sent_data:
            # short list for names of types, list of actor names, and lists for the wealth breakdowns
            vals: Tuple[List[str], List[str], List[float]] = (["Wealth in fiat"], ["darkgreen"], [1], [], [])
            static_val_len = 4
        else:
            vals = ([],)
            static_val_len = 0

        try:
            agents = sorted(
                data_collector.agent_vars["Agents"][-1],
                key=lambda x: x[0]
            )  # [:-1]
            for item in agents:
                if not self.sent_data:
                    vals[3].append(item[1].name)
                vals[0 + static_val_len].append(float(item[1].wealth()))
            self.sent_data = True
        except Exception:
            vals = []

        return vals


PortfolioTuple = Tuple[List[str], List[str], List[int],
                       List[str], List[float], List[float],
                       List[float], List[float], List[float]]


class PortfolioModule(BarGraphModule):
    """
    A bar graph that will show the bars stacked in terms of wealth of different types:
      escrowed_havvens, unescrowed_havvens, nomins, fiat
    """

    def __init__(self, series: List[Dict[str, str]], height: int = 150,
                 width: int = 500, data_collector_name: str = "datacollector",
                 fiat_values: bool = False, desc: str = "", title: str = "", group: str = "") -> None:
        super().__init__(series, height, width, data_collector_name, desc, title, group)
        self.fiat_values = fiat_values

        # ensure the data for agent names/colours only appears in the first tick
        self.sent_data = False

    def render(self, model: HavvenModel) -> PortfolioTuple:
        data_collector: "DataCollector" = getattr(
            model, self.data_collector_name
        )

        if len(data_collector.agent_vars["Agents"]) <= 1:
            self.sent_data = False

        # vals are [datasets],[colours],[bar #],[playername],[dataset 1],...[dataset n]
        if not self.sent_data:
            vals: PortfolioTuple = (["Fiat", "Escrowed Havvens", "Havvens", "Nomins", "Issued Nomins"],
                                    ["darkgreen", "darkred", "red", "deepskyblue", "blue"],
                                    [1, 1, 1, 1, 1], [], [], [], [], [], [])
            static_val_len = 4
        else:
            vals = ([], [], [], [], [])
            static_val_len = 0

        try:
            agents = sorted(
                data_collector.agent_vars["Agents"][-1],
                key=lambda x: x[0]
            )  # [:-1]

            for item in agents:
                if not self.sent_data:
                    vals[3].append(item[1].name)
                breakdown = item[1].portfolio(self.fiat_values)
                for i in range(len(breakdown)):
                    # assume that issued nomins are last
                    if i+1 == len(breakdown):
                        vals[i + static_val_len].append(-float(breakdown[i]))
                    else:
                        vals[i + static_val_len].append(float(breakdown[i]))
            self.sent_data = True
        except Exception:
            vals = []

        return vals


OrderbookValueTuple = Tuple[List[str], List[str], List[int], List[str], List[float], List[float],
                            List[float], List[float], List[float], List[float]]


class CurrentOrderModule(BarGraphModule):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ensure the data for agent names/colours only appears in the first tick
        self.sent_data = False

    def render(self, model: HavvenModel) -> OrderbookValueTuple:
        data_collector: "DataCollector" = getattr(
            model, self.data_collector_name
        )

        if len(data_collector.agent_vars["Agents"]) <= 1:
            self.sent_data = False

        # vals are [datasets],[colours],[bar #],[playername],[dataset 1],...[dataset n]
        if not self.sent_data:
            vals: OrderbookValueTuple = (
                ["NomFiatAsk",  "NomFiatBid", "HavFiatAsk", "HavFiatBid", "HavNomAsk", "HavNomBid"],
                ["deepskyblue", "#179473",    "red",        "#8C2E00",    "purple",    "#995266"],
                [1, 1, 2, 2, 3, 3], [], [], [], [], [], [], []
            )
            static_val_length = 4
        else:
            vals = ([], [], [], [], [], [])
            static_val_length = 0

        try:
            agents = sorted(
                data_collector.agent_vars["Agents"][-1],
                key=lambda x: x[0]
            )  # [:-1]

            for item in agents:
                if not self.sent_data:
                    vals[3].append(item[1].name)
                orders = item[1].orders
                nomin_fiat_ask_tot = 0
                nomin_fiat_bid_tot = 0
                havven_fiat_ask_tot = 0
                havven_fiat_bid_tot = 0
                nomin_havven_ask_tot = 0
                nomin_havven_bid_tot = 0

                for order in orders:
                    if order.book.quoted == "fiat":
                        if order.book.base == "nomins":
                            # FIAT/NOM
                            if type(order) == Ask:
                                nomin_fiat_ask_tot += order.quantity
                            if type(order) == Bid:
                                nomin_fiat_bid_tot += order.quantity
                        if order.book.base == "havvens":
                            if type(order) == Ask:
                                havven_fiat_ask_tot += order.quantity
                            if type(order) == Bid:
                                havven_fiat_bid_tot += order.quantity
                    elif order.book.quoted == "nomins":
                        if type(order) == Ask:
                            nomin_havven_ask_tot += order.quantity
                        if type(order) == Bid:
                            nomin_havven_bid_tot += order.quantity

                vals[0 + static_val_length].append(float(nomin_fiat_ask_tot))
                vals[1 + static_val_length].append(-float(nomin_fiat_bid_tot))
                vals[2 + static_val_length].append(float(havven_fiat_ask_tot))
                vals[3 + static_val_length].append(-float(havven_fiat_bid_tot))
                vals[4 + static_val_length].append(float(nomin_havven_ask_tot))
                vals[5 + static_val_length].append(-float(nomin_havven_bid_tot))
            self.sent_data = True
        except Exception as e:
            print(e)
            vals = []
        return vals


class PastOrdersModule(BarGraphModule):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ensure the data for agent names/colours only appears in the first tick
        self.sent_data = False

    def render(self, model: HavvenModel) -> OrderbookValueTuple:
        data_collector: "DataCollector" = getattr(
            model, self.data_collector_name
        )

        if len(data_collector.agent_vars["Agents"]) <= 1:
            self.sent_data = False

        # vals are [datasets],[colours],[bar #],[playername],[dataset 1],...[dataset n]
        if not self.sent_data:
            vals: OrderbookValueTuple = (
                ["NomFiatAsk",  "NomFiatBid", "HavFiatAsk", "HavFiatBid", "HavNomAsk", "HavNomBid"],
                ["deepskyblue", "#179473",    "red",        "#8C2E00",    "purple",    "#995266"],
                [1, 1, 2, 2, 3, 3], [], [], [], [], [], [], []
            )
            static_val_length = 4
        else:
            vals = ([], [], [], [], [], [])
            static_val_length = 0
        try:
            agents = sorted(
                data_collector.agent_vars["Agents"][-1],
                key=lambda x: x[0]
            )  # [:-1]

            for item in agents:
                if not self.sent_data:
                    vals[3].append(item[1].name)
                trades = item[1].trades
                nomin_fiat_ask_tot = 0
                nomin_fiat_bid_tot = 0
                havven_fiat_ask_tot = 0
                havven_fiat_bid_tot = 0
                nomin_havven_ask_tot = 0
                nomin_havven_bid_tot = 0

                for trade in trades:
                    if trade.book.quoted == "fiat":
                        if trade.book.base == "nomins":
                            # FIAT/NOM
                            if trade.buyer == item[1]:
                                nomin_fiat_ask_tot += trade.quantity
                            elif trade.seller == item[1]:
                                nomin_fiat_bid_tot += trade.quantity
                        if trade.book.base == "havvens":
                            if trade.buyer == item[1]:
                                havven_fiat_ask_tot += trade.quantity
                            elif trade.seller == item[1]:
                                havven_fiat_bid_tot += trade.quantity
                    elif trade.book.quoted == "nomins":
                        if trade.buyer == item[1]:
                            nomin_havven_ask_tot += trade.quantity
                        elif trade.seller == item[1]:
                            nomin_havven_bid_tot += trade.quantity

                vals[0 + static_val_length].append(float(nomin_fiat_ask_tot))
                vals[1 + static_val_length].append(-float(nomin_fiat_bid_tot))
                vals[2 + static_val_length].append(float(havven_fiat_ask_tot))
                vals[3 + static_val_length].append(-float(havven_fiat_bid_tot))
                vals[4 + static_val_length].append(float(nomin_havven_ask_tot))
                vals[5 + static_val_length].append(-float(nomin_havven_bid_tot))

            self.sent_data = True
        except Exception as e:
            print(e)
            vals = []
        return vals
