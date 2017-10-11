"""model.py: The havven model itself lives here."""

from typing import Callable, Optional
import random

from scipy.stats import skewnorm

from mesa import Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector

import orderbook as ob
import modelstats as ms
import agents as ag
from config import HavvenSettings, FeeConfig


# Function signatures for transfers.
TransferTest = Callable[[ag.MarketPlayer, float], bool]
TransferFunction = Callable[[ag.MarketPlayer, ag.MarketPlayer, float], bool]


class Havven(Model):
    """
    An agent-based model of the Havven stablecoin system. This class will
      provide the basic market functionality of havven, an exchange, and a
      place for the market agents to live and interact.
    The aim is to stabilise the nomin price, but we would also like to measure
      other quantities including liquidity, volatility, wealth concentration,
      velocity of money and so on.
    """

    def __init__(self, N: int, max_fiat: float = 1000,
                 match_on_order: bool = True) -> None:
        # Mesa setup
        super().__init__()
        self.schedule = RandomActivation(self)
        self.datacollector = DataCollector(
            model_reporters={
                "": lambda x: 0,  # Note: workaround for showing labels (more info server.py)
                "Havven Nomins": lambda h: h.nomins,
                "Havven Curits": lambda h: h.curits,
                "Havven Fiat": lambda h: h.fiat,
                "Gini": ms.gini,
                "Nomins": lambda h: h.nomin_supply,
                "Escrowed Curits": lambda h: h.escrowed_curits,
                "Wealth SD": ms.wealth_sd,
                "Max Wealth": ms.max_wealth,
                "Min Wealth": ms.min_wealth,
                "Profit %": ms.mean_profit_fraction,
                "Curit Demand": ms.curit_demand,
                "Curit Supply": ms.curit_supply,
                "Nomin Demand": ms.nomin_demand,
                "Nomin Supply": ms.nomin_supply,
                "Fiat Demand": ms.fiat_demand,
                "Fiat Supply": ms.fiat_supply,
                "Fee Pool": lambda h: h.nomins,
                "Fees Distributed": lambda h: h.fees_distributed,
                "NomCurOrderBook": lambda h: h.cur_nom_market,
                "FiatCurOrderBook": lambda h: h.cur_fiat_market,
                "FiatNomOrderBook": lambda h: h.nom_fiat_market
            }, agent_reporters={
                "Wealth": lambda agent: agent.wealth,
                "Name": lambda agent: agent.name
            })

        self.time: int = 1

        # Create the model settings objects

        self.settings = HavvenSettings()

        # Add the market participants
        total_endowment = 0.0
        self.num_agents: int = N
        for i in range(self.num_agents):
            endowment = int(skewnorm.rvs(100)*max_fiat)
            a = ag.Banker(i, self, fiat=endowment)
            self.schedule.add(a)
            total_endowment += endowment

        randomizer = ag.Randomizer(i+1, self, fiat=max_fiat)
        self.schedule.add(randomizer)

        reserve_bank = ag.MarketPlayer(self.num_agents+1, self, 0)
        self.endow_curits(reserve_bank, 6 * N * max_fiat)
        self.schedule.add(reserve_bank)
        reserve_bank.sell_curits_for_fiat(N * max_fiat * 3)
        reserve_bank.sell_curits_for_nomins(N * max_fiat * 3)

    def fiat_value(self, curits: float, nomins: float, fiat: float) -> float:
        """Return the equivalent fiat value of the given currency basket."""
        return self.cur_to_fiat(curits) + self.nom_to_fiat(nomins) + fiat

    def endow_curits(self, agent: ag.MarketPlayer, curits: float) -> None:
        """Grant an agent an endowment of curits."""
        if curits > 0:
            value = min(self.curits, curits)
            agent.curits += value
            self.curits -= value

    def distribute_fees(self) -> None:
        """Distribute currently held nomins to holders of curits."""
        # Different fee modes:
        #  * distributed by held curits
        # TODO: * distribute by escrowed curits
        # TODO: * distribute by issued nomins
        # TODO: * distribute by motility

        pre_fees = self.nomins
        for agent in self.schedule.agents:
            if self.nomins == 0:
                break
            qty = min(agent.issued_nomins / self.nomins, self.nomins)
            agent.nomins += qty
            self.nomins -= qty
            self.fees_distributed += qty

    def step(self) -> None:
        """Advance the model by one step."""
        # Agents submit trades
        self.schedule.step()

        # Resolve outstanding trades
        if not self.match_on_order:
            self.cur_nom_market.match()
            self.cur_fiat_market.match()
            self.nom_fiat_market.match()

        # Distribute fees periodically.
        if (self.time % self.fee_period) == 0:
            self.distribute_fees()

        # Collect data
        self.datacollector.collect(self)

        self.time += 1
