"""model.py: The havven model itself lives here."""

from decimal import Decimal as Dec

from mesa import Model
from mesa.time import RandomActivation
from mesa.datacollection import DataCollector

import stats
import agents as ag
from managers import (HavvenManager, MarketManager,
                      FeeManager, Mint,
                      AgentManager)


class Havven(Model):
    """
    An agent-based model of the Havven stablecoin system. This class will
      provide the basic market functionality of havven, an exchange, and a
      place for the market agents to live and interact.
    The aim is to stabilise the nomin price, but we would also like to measure
      other quantities including liquidity, volatility, wealth concentration,
      velocity of money and so on.
    """

    def __init__(self, num_agents: int, init_value: float = 1000.0,
                 utilisation_ratio_max: float = 1.0,
                 match_on_order: bool = True) -> None:

        # Mesa setup
        super().__init__()
        self.schedule = RandomActivation(self)
        self.datacollector = DataCollector(
            model_reporters={
                "0": lambda x: 0,  # Note: workaround for showing labels (more info server.py)
                "1": lambda x: 1,
                "Nomin Price": lambda h: float(h.market_manager.nomin_fiat_market.price),
                "Nomin Ask": lambda h: float(h.market_manager.nomin_fiat_market.lowest_ask_price()),
                "Nomin Bid": lambda h: float(h.market_manager.nomin_fiat_market.highest_bid_price()),
                "Curit Price": lambda h: float(h.market_manager.curit_fiat_market.price),
                "Curit Ask": lambda h: float(h.market_manager.curit_fiat_market.lowest_ask_price()),
                "Curit Bid": lambda h: float(h.market_manager.curit_fiat_market.highest_bid_price()),
                "Curit/Nomin Price": lambda h: float(h.market_manager.curit_nomin_market.price),
                "Curit/Nomin Ask": lambda h: float(h.market_manager.curit_nomin_market.lowest_ask_price()),
                "Curit/Nomin Bid": lambda h: float(h.market_manager.curit_nomin_market.highest_bid_price()),
                "Havven Nomins": lambda h: float(h.manager.nomins),
                "Havven Curits": lambda h: float(h.manager.curits),
                "Havven Fiat": lambda h: float(h.manager.fiat),
                "Gini": stats.gini,
                "Nomins": lambda h: float(h.manager.nomin_supply),
                "Escrowed Curits": lambda h: float(h.manager.escrowed_curits),
                #"Wealth SD": stats.wealth_sd,
                "Max Wealth": stats.max_wealth,
                "Min Wealth": stats.min_wealth,
                "Avg Profit %": lambda h: round(100*stats.mean_profit_fraction(h), 3),
                "Bank Profit %": lambda h: round(100*stats.mean_banker_profit_fraction(h), 3),
                "Arb Profit %": lambda h: round(100*stats.mean_arb_profit_fraction(h), 3),
                "Rand Profit %": lambda h: round(100*stats.mean_rand_profit_fraction(h), 3),
                "NomShort Profit %": lambda h: round(100*stats.mean_nomshort_profit_fraction(h), 3),
                "Curit Demand": stats.curit_demand,
                "Curit Supply": stats.curit_supply,
                "Nomin Demand": stats.nomin_demand,
                "Nomin Supply": stats.nomin_supply,
                "Fiat Demand": stats.fiat_demand,
                "Fiat Supply": stats.fiat_supply,
                "Fee Pool": lambda h: float(h.manager.nomins),
                "Fees Distributed": lambda h: float(h.fee_manager.fees_distributed),
                "NominFiatOrderBook": lambda h: h.market_manager.nomin_fiat_market,
                "CuritFiatOrderBook": lambda h: h.market_manager.curit_fiat_market,
                "CuritNominOrderBook": lambda h: h.market_manager.curit_nomin_market
            }, agent_reporters={
                "Agents": lambda a: a,
            })

        # Initiate time itself.
        self.time: int = 0

        # Initialise simulation managers.
        self.manager = HavvenManager(Dec(utilisation_ratio_max), match_on_order)
        self.fee_manager = FeeManager(self.manager)
        self.market_manager = MarketManager(self.manager, self.fee_manager)
        self.mint = Mint(self.manager, self.market_manager)

        # Set the market player fractions and endowment.
        fractions = {ag.Banker: 0.2,
                     ag.Arbitrageur: 0.2,
                     ag.Randomizer: 0.3,
                     ag.NominShorter: 0.15,
                     ag.CuritEscrowNominShorter: 0.15}
        self.agent_manager = AgentManager(self, num_agents,
                                          fractions, Dec(init_value))

    def fiat_value(self, curits: Dec = Dec('0'), nomins: Dec = Dec('0'),
                   fiat: Dec = Dec('0')) -> Dec:
        """Return the equivalent fiat value of the given currency basket."""
        return self.market_manager.curits_to_fiat(curits) + \
            self.market_manager.nomins_to_fiat(nomins) + fiat

    def endow_curits(self, agent: ag.MarketPlayer, curits: Dec) -> None:
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
            self.market_manager.curit_nomin_market.match()
            self.market_manager.curit_fiat_market.match()
            self.market_manager.nomin_fiat_market.match()

        # Distribute fees periodically.
        if (self.time % self.fee_manager.fee_period) == 0:
            self.fee_manager.distribute_fees(self.schedule.agents)

        # Collect data
        self.datacollector.collect(self)

        self.time += 1
