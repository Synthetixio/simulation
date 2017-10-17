"""model.py: The havven model itself lives here."""

from scipy.stats import skewnorm
from decimal import Decimal as Dec

from mesa import Model
from mesa.time import RandomActivation
from mesa.datacollection import DataCollector

import stats
import agents as ag
from managers import HavvenManager, MarketManager, FeeManager, Mint


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

        self.time: int = 1

        # Create the model settings objects

        self.manager = HavvenManager(Dec(utilisation_ratio_max), match_on_order)
        self.fee_manager = FeeManager(self.manager)
        self.market_manager = MarketManager(self.manager, self.fee_manager)
        self.mint = Mint(self.manager, self.market_manager)

        # Create the market players

        fractions = {"banks": 0.2,
                     "arbs": 0.2,
                     "rands": 0.3,
                     "nomin shorter": 0.15,
                     "escrow nomin shorter": 0.15}

        num_banks = int(num_agents * fractions["banks"])
        num_rands = int(num_agents * fractions["rands"])
        num_arbs = int(num_agents * fractions["arbs"])
        nomin_shorters = int(num_agents * fractions["nomin shorter"])
        escrow_nomin_shorters = int(num_agents * fractions["escrow nomin shorter"])

        # convert init_value to decimal type, be careful with floats!
        init_value_d = Dec(init_value)

        i = 0

        for _ in range(num_banks):
            endowment = HavvenManager.round_decimal(Dec(skewnorm.rvs(100))*init_value_d)
            self.schedule.add(ag.Banker(i, self, fiat=endowment))
            i += 1
        for _ in range(num_rands):
            rand = ag.Randomizer(i, self, fiat=init_value_d)
            self.endow_curits(rand, Dec(3)*init_value_d)
            self.schedule.add(rand)
            i += 1
        for _ in range(num_arbs):
            arb = ag.Arbitrageur(i, self, fiat=HavvenManager.round_decimal(init_value_d/Dec(2)))
            self.endow_curits(arb, HavvenManager.round_decimal(init_value_d/Dec(2)))
            self.schedule.add(arb)
            i += 1
        for _ in range(nomin_shorters):
            nomin_shorter = ag.NominShorter(i, self, nomins=init_value_d*Dec(2))
            self.schedule.add(nomin_shorter)
            i += 1
        for _ in range(escrow_nomin_shorters):
            escrow_nomin_shorter = ag.CuritEscrowNominShorter(i, self, curits=init_value_d*Dec(2))
            self.schedule.add(escrow_nomin_shorter)
            i += 1

        central_bank = ag.CentralBank(
            i, self, fiat=Dec(num_agents * init_value_d), curit_target=Dec('1.0')
        )
        self.endow_curits(central_bank, Dec(num_agents * init_value_d))
        self.schedule.add(central_bank)

        for agent in self.schedule.agents:
            agent.reset_initial_wealth()

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
