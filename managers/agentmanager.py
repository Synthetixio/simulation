from decimal import Decimal as Dec
from typing import Dict, List

import agents as ag


class AgentManager:
    """Manages agent populations."""

    def __init__(self,
                 havven_model,
                 num_agents: int,
                 agent_fractions: Dict[str, float],
                 agent_settings: Dict[str, any]) -> None:
        """
        :param havven_model: a reference to the sim itself.
        :param num_agents: the number of agents to include in this simulation (plus or minus a handful).
        :param agent_fractions: the vector which sets the proportions of each agent in the model. Will be normalised.
        :param agent_settings: dict holding values from setting file
         - init_value: the initial value from which to calculate agent endowments.
         - agent_minimum: the minimum number of each type of agent to include in the simulation. 1 by default.
        """

        self.wealth_parameter = agent_settings['wealth_parameter']
        self.wage_parameter = agent_settings['wage_parameter']
        self.liquidation_parameter = agent_settings['liquidation_parameter']
        self.agent_minimum = agent_settings['agent_minimum']

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
                    normalised_fractions[name] = agent_fractions[name] / total_value
        agent_fractions = normalised_fractions

        # Create the agents themselves.
        self.running_player_total = 0
        for agent_type in agent_fractions:
            total = max(
                self.agent_minimum,
                int(num_agents * agent_fractions[agent_type])
            )

            for i in range(total):
                agent = ag.player_names[agent_type](self.running_player_total, self.havven_model)
                agent.setup(self.wealth_parameter, self.wage_parameter, self.liquidation_parameter)
                self.havven_model.schedule.add(agent)
                self.agents[agent_type].append(agent)
                self.running_player_total += 1

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

    def add_issuance_controller(self) -> 'ag.IssuanceController':
        issuance_controller = ag.IssuanceController(self.running_player_total, self.havven_model)

        # give the issuance controller some extra fiat/nomins to avoid rounding errors
        issuance_controller.fiat += Dec('1')
        issuance_controller.nomins += Dec('1')

        self.running_player_total += 1
        self.havven_model.schedule.add(issuance_controller)
        self.agents['others'].append(issuance_controller)
        return issuance_controller

    def add_havven_foundation(self, initial_c: Dec, foundation_cut: Dec) -> 'ag.HavvenFoundation':
        havven_foundation = ag.HavvenFoundation(self.running_player_total, self.havven_model)
        self.running_player_total += 1

        havven_foundation_initial_c = Dec(initial_c)
        self.havven_model.endow_havvens(
            havven_foundation,
            Dec(foundation_cut) * self.havven_model.manager.havvens
        )

        havven_foundation.issued_nomins = havven_foundation.havvens * havven_foundation_initial_c
        havven_foundation.nomins = havven_foundation.havvens * havven_foundation_initial_c

        self.havven_model.manager.issued_nomins += havven_foundation.havvens * havven_foundation_initial_c
        self.agents['others'].append(havven_foundation)
        return havven_foundation
