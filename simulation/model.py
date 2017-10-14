"""model.py: The havven model itself lives here."""

from scipy.stats import skewnorm

from mesa import Model
from mesa.time import RandomActivation
from mesa.datacollection import DataCollector

import stats
import agents as ag
from managers import HavvenManager, MarketManager, FeeManager, Mint
from orderbook import OrderBook


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
                "Nomin Price": lambda h: h.market_manager.nomin_fiat_market.price,
                "Nomin Ask": lambda h: h.market_manager.nomin_fiat_market.lowest_ask_price(),
                "Nomin Bid": lambda h: h.market_manager.nomin_fiat_market.highest_bid_price(),
                "Curit Price": lambda h: h.market_manager.curit_fiat_market.price,
                "Curit Ask": lambda h: h.market_manager.curit_fiat_market.lowest_ask_price(),
                "Curit Bid": lambda h: h.market_manager.curit_fiat_market.highest_bid_price(),
                "Curit/Nomin Price": lambda h: h.market_manager.curit_nomin_market.price,
                "Curit/Nomin Ask": lambda h: h.market_manager.curit_nomin_market.lowest_ask_price(),
                "Curit/Nomin Bid": lambda h: h.market_manager.curit_nomin_market.highest_bid_price(),
                "Havven Nomins": lambda h: h.manager.nomins,
                "Havven Curits": lambda h: h.manager.curits,
                "Havven Fiat": lambda h: h.manager.fiat,
                "Gini": stats.gini,
                "Nomins": lambda h: h.manager.nomin_supply,
                "Escrowed Curits": lambda h: h.manager.escrowed_curits,
                #"Wealth SD": stats.wealth_sd,
                "Max Wealth": stats.max_wealth,
                "Min Wealth": stats.min_wealth,
                "Avg Profit %": lambda h: round(100*stats.mean_profit_fraction(h), 3),
                "Bank Profit %": lambda h: round(100*stats.mean_banker_profit_fraction(h), 3),
                "Arb Profit %": lambda h: round(100*stats.mean_arb_profit_fraction(h), 3),
                "Rand Profit %": lambda h: round(100*stats.mean_rand_profit_fraction(h), 3),
                "Curit Demand": stats.curit_demand,
                "Curit Supply": stats.curit_supply,
                "Nomin Demand": stats.nomin_demand,
                "Nomin Supply": stats.nomin_supply,
                "Fiat Demand": stats.fiat_demand,
                "Fiat Supply": stats.fiat_supply,
                "Fee Pool": lambda h: h.manager.nomins,
                "Fees Distributed": lambda h: h.fee_manager.fees_distributed,
                "NominFiatOrderBook": lambda h: h.market_manager.nomin_fiat_market,
                "CuritFiatOrderBook": lambda h: h.market_manager.curit_fiat_market,
                "CuritNominOrderBook": lambda h: h.market_manager.curit_nomin_market
            }, agent_reporters={
                "Agents": lambda agent: agent,
            })

        self.time: int = 1

        # Create the model settings objects

        self.manager = HavvenManager(utilisation_ratio_max, match_on_order)
        self.fee_manager = FeeManager(self.manager)
        self.market_manager = MarketManager(self.manager, self.fee_manager)
        self.mint = Mint(self.manager, self.market_manager)

        # Create the market players

        fractions = {"banks": 0.25,
                     "arbs": 0.25,
                     "rands": 0.5}

        num_banks = int(num_agents * fractions["banks"])
        num_rands = int(num_agents * fractions["rands"])
        num_arbs = int(num_agents * fractions["arbs"])

        i = 0

        for _ in range(num_banks):
            endowment = int(skewnorm.rvs(100)*max_fiat)
            self.schedule.add(ag.Banker(i, self, fiat=endowment))
            i += 1
        for _ in range(num_rands):
            rand = ag.Randomizer(i, self, fiat=max_fiat)
            self.endow_curits(rand, 3*max_fiat)
            self.schedule.add(rand)
            i += 1
        for _ in range(num_arbs):
            self.schedule.add(ag.Arbitrageur(i, self, fiat=max_fiat))
            i += 1

        central_bank = ag.CentralBank(i, self, fiat = (0.5 * num_agents * max_fiat), nomin_target=1.0)
        self.endow_curits(central_bank, (num_agents * max_fiat))
        self.schedule.add(central_bank)

        for agent in self.schedule.agents:
            agent.reset_initial_wealth()

    def fiat_value(self, curits: float = 0.0, nomins: float = 0.0, fiat: float = 0.0) -> float:
        """Return the equivalent fiat value of the given currency basket."""
        return self.market_manager.curits_to_fiat(curits) + \
               self.market_manager.nomins_to_fiat(nomins) + fiat

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
            self.market_manager.curit_nomin_market.match()
            self.market_manager.curit_fiat_market.match()
            self.market_manager.nomin_fiat_market.match()

        # Distribute fees periodically.
        if (self.time % self.fee_manager.fee_period) == 0:
            self.fee_manager.distribute_fees(self.schedule.agents)

        # Collect data
        self.datacollector.collect(self)

        self.time += 1
