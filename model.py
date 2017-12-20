"""model.py: The Havven model itself lives here."""

from decimal import Decimal as Dec
from typing import Dict, Any

from mesa import Model
from mesa.time import RandomActivation

import agents as ag
from managers import (HavvenManager, MarketManager,
                      FeeManager, Mint,
                      AgentManager)
from util import stats


class HavvenModel(Model):
    """
    An agent-based model of the Havven stablecoin system. This class will
      provide the basic market functionality of Havven, an exchange, and a
      place for the market agents to live and interact.
    The aim is to stabilise the nomin price, but we would also like to measure
      other quantities including liquidity, volatility, wealth concentration,
      velocity of money and so on.
    """
    def __init__(self,
                 model_settings: Dict[str, Any],
                 fee_settings: Dict[str, Any],
                 agent_settings: Dict[str, Any],
                 havven_settings: Dict[str, Any]) -> None:
        """

        :param model_settings: Setting that are modifiable on the frontend
         - agent_fraction: what percentage of each agent to use
         - num_agents: the total number of agents to use
         - utilisation_ratio_max: the max utilisation ratio for nomin issuance against havvens
         - continuous_order_matching: whether to match orders as they come,
         or at the end of each tick
        :param fee_settings: explained in feemanager.py
        :param agent_settings: explained in agentmanager.py
        :param havven_settings: explained in havvenmanager.py
        """
        agent_fractions = model_settings['agent_fractions']
        num_agents = model_settings['num_agents']
        utilisation_ratio_max = model_settings['utilisation_ratio_max']
        continuous_order_matching = model_settings['continuous_order_matching']

        # Mesa setup.
        super().__init__()

        # The schedule will activate agents in a random order per step.
        self.schedule = RandomActivation(self)

        # Set up data collection.
        self.datacollector = stats.create_datacollector()

        # Initialise simulation managers.
        self.manager = HavvenManager(
            Dec(utilisation_ratio_max),
            continuous_order_matching,
            havven_settings
        )
        self.fee_manager = FeeManager(
            self.manager,
            fee_settings
        )
        self.market_manager = MarketManager(self.manager, self.fee_manager)
        self.mint = Mint(self.manager, self.market_manager)

        self.agent_manager = AgentManager(
            self,
            num_agents,
            agent_fractions,
            agent_settings
        )

    def fiat_value(self, havvens=Dec('0'), nomins=Dec('0'),
                   fiat=Dec('0')) -> Dec:
        """Return the equivalent fiat value of the given currency basket."""
        return self.market_manager.havvens_to_fiat(havvens) + \
            self.market_manager.nomins_to_fiat(nomins) + fiat

    def endow_havvens(self, agent: "ag.MarketPlayer", havvens: Dec) -> None:
        """Grant an agent an endowment of havvens."""
        if havvens > 0:
            value = min(self.manager.havvens, havvens)
            agent.havvens += value
            self.manager.havvens -= value

    def step(self) -> None:
        """Advance the model by one step."""
        # Agents submit trades.
        self.schedule.step()

        self.market_manager.havven_nomin_market.step_history()
        self.market_manager.havven_fiat_market.step_history()
        self.market_manager.nomin_fiat_market.step_history()

        # Resolve outstanding trades.
        if not self.manager.continuous_order_matching:
            self.market_manager.havven_nomin_market.match()
            self.market_manager.havven_fiat_market.match()
            self.market_manager.nomin_fiat_market.match()

        # Distribute fees periodically.
        if (self.manager.time % self.fee_manager.fee_period) == 0:
            self.fee_manager.distribute_fees(self.schedule.agents)

        # Collect data.
        self.datacollector.collect(self)

        # Advance Time Itself.
        self.manager.time += 1
