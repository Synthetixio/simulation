"""model.py: The Havven model itself lives here."""

from decimal import Decimal as Dec
from typing import Dict, Any

from mesa import Model
from mesa.time import RandomActivation

import agents as ag
from managers import HavvenManager, AgentManager, FeeManager, MarketManager, Mint
from core import stats


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
                 havven_settings: Dict[str, Any],
                 mint_settings: Dict[str, Any]) -> None:
        """
        :param model_settings: Setting that are modifiable on the frontend
         - agent_fraction: what percentage of each agent to use
         - num_agents: the total number of agents to use
         - utilisation_ratio_max: the max utilisation ratio for nomin issuance against havvens
         or at the end of each tick
        :param fee_settings: explained in feemanager.py
        :param agent_settings: explained in agentmanager.py
        :param havven_settings: explained in havvenmanager.py
        """
        # since this can be set on the frontend, it is added to model_settings
        agent_fractions = model_settings['agent_fractions']
        num_agents = model_settings['num_agents']

        # Mesa setup.
        super().__init__()

        # The schedule will activate agents in a random order per step.
        self.schedule = RandomActivation(self)

        # Set up data collection.
        self.datacollector = stats.create_datacollector()

        # Initialise simulation managers.
        self.manager = HavvenManager(
            havven_settings,
            self
        )

        self.fee_manager = FeeManager(
            self.manager,
            fee_settings
        )
        self.market_manager = MarketManager(self.manager, self.fee_manager)

        self.mint = Mint(self.manager, self.market_manager, self.fee_manager, mint_settings)

        self.agent_manager = AgentManager(
            self,
            num_agents,
            agent_fractions,
            agent_settings
        )

        issuance_controller = self.agent_manager.add_issuance_controller()
        self.mint.add_issuance_controller(issuance_controller)

        self.havven_foundation = None
        if agent_settings['havven_foundation_enabled']:
            self.havven_foundation = self.agent_manager.add_havven_foundation(
                agent_settings['havven_foundation_initial_c'],
                agent_settings['havven_foundation_cut']
            )

        self.mint.calculate_copt_cmax()
        self.datacollector.collect(self)

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

        # Distribute fees periodically.
        if ((self.manager.time + 1) % self.fee_manager.fee_period) == 0:
            if self.mint.use_copt:
                self.fee_manager.distribute_fees_using_collateralisation_targets(
                    self.schedule.agents, self.mint.copt, self.mint.cmax
                )

        # calculate copt and cmax after fees distributed to reward good players
        self.mint.calculate_copt_cmax()

        # Collect data.
        self.datacollector.collect(self)

        # Advance Time Itself.
        self.manager.time += 1
