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
                 test_mode: bool = False) -> None:

        # A reference to the havven sim itself.
        self.havven_model = havven_model

        # Lists of each type of agent.
        self.agents: Dict[str, List[ag.MarketPlayer]] = {
            name: [] for name in ag.player_names
        }
        self.agents["others"] = []
        if test_mode:
            return
        else:
            # Normalise the fractions of the population each agent occupies.
            total_value = sum(agent_fractions.values())
            result = {}
            if total_value > 0:
                for name in ag.player_names:
                    if name in agent_fractions:
                        result[name] = agent_fractions[name]/total_value
                        # always have a merchant

            agent_fractions = result

            # create each agent with custom
            total_players = 0
            for item in result:
                total = max(1, int(num_agents*agent_fractions[item]) if item in agent_fractions else 0)
                for i in range(total):
                    agent = ag.player_names[item](total_players, self.havven_model)
                    agent.setup(init_value)
                    self.havven_model.schedule.add(agent)
                    self.agents[item].append(agent)
                    total_players += 1

            # central_bank = ag.CentralBank(
            #     total_players, self.havven_model, fiat=Dec(num_agents * init_value),
            #     nomin_target=Dec('1.0')
            # )
            # self.havven_model.endow_havvens(central_bank,
            #                          Dec(num_agents * init_value))
            # self.havven_model.schedule.add(central_bank)
            # self.agents["others"].append(central_bank)

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
