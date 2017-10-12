"""model.py: The havven model itself lives here."""

from scipy.stats import skewnorm

from mesa import Model
from mesa.time import RandomActivation
from mesa.datacollection import DataCollector

import modelstats as ms
import agents as ag
from config import FeeConfig
from manager import HavvenManager, TradeManager, FeeManager


class Havven(Model):
    """
    An agent-based model of the Havven stablecoin system. This class will
      provide the basic market functionality of havven, an exchange, and a
      place for the market agents to live and interact.
    The aim is to stabilise the nomin price, but we would also like to measure
      other quantities including liquidity, volatility, wealth concentration,
      velocity of money and so on.
    """

    def __init__(self, num_agents: int, max_fiat: float = 1000,
                 utilisation_ratio_max: float = 1.0,
                 match_on_order: bool = True) -> None:
        # Mesa setup
        super().__init__()
        self.schedule = RandomActivation(self)
        self.datacollector = DataCollector(
            model_reporters={
                "0": lambda x: 0,  # Note: workaround for showing labels (more info server.py)
                "1": lambda x: 1,
                "Nomin Price": lambda h: h.trade_manager.nomin_fiat_price,
                "Nomin Ask": lambda h: h.trade_manager.nom_fiat_market.lowest_ask_price(),
                "Nomin Bid": lambda h: h.trade_manager.nom_fiat_market.highest_bid_price(),
                "Curit Price": lambda h: h.trade_manager.curit_fiat_price,
                "Curit Ask": lambda h: h.trade_manager.cur_fiat_market.lowest_ask_price(),
                "Curit Bid": lambda h: h.trade_manager.cur_fiat_market.highest_bid_price(),
                "Curit/Nomin Price": lambda h: h.trade_manager.curit_nomin_price,
                "Curit/Nomin Ask": lambda h: h.trade_manager.cur_nom_market.lowest_ask_price(),
                "Curit/Nomin Bid": lambda h: h.trade_manager.cur_nom_market.highest_bid_price(),
                "Havven Nomins": lambda h: h.manager.nomins,
                "Havven Curits": lambda h: h.manager.curits,
                "Havven Fiat": lambda h: h.manager.fiat,
                "Gini": ms.gini,
                "Nomins": lambda h: h.manager.nomin_supply,
                "Escrowed Curits": lambda h: h.manager.escrowed_curits,
                "Wealth SD": ms.wealth_sd,
                "Max Wealth": ms.max_wealth,
                "Min Wealth": ms.min_wealth,
                "Avg Profit %": lambda h: round(100*ms.mean_profit_fraction(h), 3),
                "Bank Profit %": lambda h: round(100*ms.mean_banker_profit_fraction(h), 3),
                "Arb Profit %": lambda h: round(100*ms.mean_arb_profit_fraction(h), 3),
                "Rand Profit %": lambda h: round(100*ms.mean_rand_profit_fraction(h), 3),
                "Curit Demand": ms.curit_demand,
                "Curit Supply": ms.curit_supply,
                "Nomin Demand": ms.nomin_demand,
                "Nomin Supply": ms.nomin_supply,
                "Fiat Demand": ms.fiat_demand,
                "Fiat Supply": ms.fiat_supply,
                "Fee Pool": lambda h: h.manager.nomins,
                "Fees Distributed": lambda h: h.fee_manager.fees_distributed,
                "NomFiatOrderBook": lambda h: h.trade_manager.nom_fiat_market,
                "CurFiatOrderBook": lambda h: h.trade_manager.cur_fiat_market,
                "CurNomOrderBook": lambda h: h.trade_manager.cur_nom_market
            }, agent_reporters={
                "Wealth": lambda agent: agent.wealth,
                "Name": lambda agent: agent.name
            })

        self.time: int = 1

        # Create the model settings objects

        self.manager = HavvenManager(num_agents, utilisation_ratio_max, match_on_order)

        self.fee_manager = FeeManager(self.manager)
        self.trade_manager = TradeManager(self.manager, self.fee_manager)

        # Create the market players

        fractions = {"banks": 0.25,
                     "arbs": 0.25,
                     "rands": 0.5}

        num_banks = int(self.manager.num_agents * fractions["banks"])
        num_rands = int(self.manager.num_agents * fractions["rands"])
        num_arbs = int(self.manager.num_agents * fractions["arbs"])

        i = 0

        for _ in range(num_banks):
            endowment = int(skewnorm.rvs(100)*max_fiat)
            self.schedule.add(ag.Banker(i, self, fiat=endowment))
            i += 1
        for _ in range(num_rands):
            self.schedule.add(ag.Randomizer(i, self, fiat=3*max_fiat))
            i += 1
        for _ in range(num_arbs):
            arbitrageur = ag.Arbitrageur(i, self, 0)
            self.endow_curits(arbitrageur, max_fiat)
            self.schedule.add(arbitrageur)
            i += 1

        reserve_bank = ag.MarketPlayer(i, self, 0)
        self.endow_curits(reserve_bank, 6 * self.manager.num_agents * max_fiat)
        self.schedule.add(reserve_bank)
        reserve_bank.sell_curits_for_fiat(self.manager.num_agents * max_fiat * 3)
        reserve_bank.sell_curits_for_nomins(self.manager.num_agents * max_fiat * 3)

        for a in self.schedule.agents:
            a.reset_initial_wealth()

    def fiat_value(self, curits: float, nomins: float, fiat: float) -> float:
        """Return the equivalent fiat value of the given currency basket."""
        return self.trade_manager.cur_to_fiat(curits) + self.trade_manager.nom_to_fiat(nomins) + fiat

    def endow_curits(self, agent: ag.MarketPlayer, curits: float) -> None:
        """Grant an agent an endowment of curits."""
        if curits > 0:
            value = min(self.manager.curits, curits)
            agent.curits += value
            self.manager.curits -= value

    def step(self) -> None:
        """Advance the model by one step."""
        # Agents submit trades
        self.schedule.step()

        # Resolve outstanding trades
        if not self.manager.match_on_order:
            self.trade_manager.cur_nom_market.match()
            self.trade_manager.cur_fiat_market.match()
            self.trade_manager.nom_fiat_market.match()

        # Distribute fees periodically.
        if (self.time % FeeConfig.fee_period) == 0:
            self.fee_manager.distribute_fees(self.schedule.agents)

        # Collect data
        self.datacollector.collect(self)

        self.time += 1
