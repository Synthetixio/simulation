from typing import Dict, List
from decimal import Decimal as Dec

import agents as ag

from .havvenmanager import HavvenManager
import model


class AgentManager:
    """Manages agent populations."""

    def __init__(self,
                 havven_model: "model.HavvenModel",
                 num_agents: int,
                 agent_fractions: Dict[str, float],
                 init_value: Dec,
                 agent_minimum: int = 1) -> None:
        """
        :param havven_model: a reference to the sim itself.
        :param num_agents: the number of agents to include in this simulation (plus or minus a handful).
        :param agent_fractions: the vector which sets the proportions of each agent in the model. Will be normalised.
        :param init_value: the initial value from which to calculate agent endowments.
        :param agent_minimum: the minimum number of each type of agent to include in the simulation. 1 by default.
        """

        # A reference to the Havven sim itself.
        self.havven_model = havven_model

        # Lists of each type of agent.
        self.agents: Dict[str, List[ag.MarketPlayer]] = {
            name: [] for name in ag.player_names
        }
        self.agents["others"] = []

        # Normalise the fractions of the population each agent occupies.
        total_value = sum(agent_fractions.values())
        normalised_fractions = {}
        if total_value > 0:
            for name in ag.player_names:
                if name in agent_fractions:
                    normalised_fractions[name] = agent_fractions[name]/total_value
        agent_fractions = normalised_fractions

        # Create the agents themselves.
        running_player_total = 0
        for agent_type in agent_fractions:
            total = max(agent_minimum, int(num_agents*agent_fractions[agent_type])
                                           if agent_type in agent_fractions else 0)

            for i in range(total):
                agent = ag.player_names[agent_type](running_player_total, self.havven_model)
                agent.setup(init_value)
                self.havven_model.schedule.add(agent)
                self.agents[agent_type].append(agent)
                running_player_total += 1

        # Add a central stabilisation bank
        # self._add_central_bank(running_player_total, num_agents, init_value)

        # Now that each agent has its initial endowment, make them remember it.
        for agent in self.havven_model.schedule.agents:
            agent.reset_initial_wealth()

    def add(self, agent):
        self.havven_model.schedule.add(agent)
        for name, item in ag.player_names.items():
            if type(agent) == item:
                self.agents[name].append(agent)
                return
        else:
            self.agents['others'].append(agent)

    def _add_central_bank(self, unique_id, num_agents, init_value):
        central_bank = ag.CentralBank(
            unique_id, self.havven_model, fiat=Dec(num_agents * init_value),
            nomin_target=Dec('1.0')
        )
        self.havven_model.endow_havvens(central_bank,
                                 Dec(num_agents * init_value))
        self.havven_model.schedule.add(central_bank)
        self.agents["others"].append(central_bank)
