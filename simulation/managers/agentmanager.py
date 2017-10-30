from typing import Dict, List
from decimal import Decimal as Dec

from scipy.stats import skewnorm

import agents as ag

from .havvenmanager import HavvenManager
import model


class AgentManager:
    """Manages agent populations."""

    def __init__(self,
                 havven: "model.Havven",
                 num_agents: int,
                 agent_fractions: Dict[str, float],
                 init_value: Dec) -> None:
        # A reference to the havven sim itself.
        self.havven = havven

        # Lists of each type of agent.
        self.bankers: List[ag.Banker] = []
        self.randomizers: List[ag.Randomizer] = []
        self.arbitrageurs: List[ag.Arbitrageur] = []
        self.nomin_shorters: List[ag.NominShorter] = []
        self.escrow_nomin_shorters: List[ag.CuritEscrowNominShorter] = []
        self.others = []

        # Normalise the fractions of the population each agent occupies.
        total_value = sum(agent_fractions.values())
        result = {}
        if total_value > 0:
            for k in agent_fractions:
                if k == 'Banker':
                    result[ag.Banker] = agent_fractions[k]/total_value
                if k == 'Randomizer':
                    result[ag.Randomizer] = agent_fractions[k]/total_value
                if k == 'Arbitrageur':
                    result[ag.Arbitrageur] = agent_fractions[k]/total_value
                if k == 'NominShorter':
                    result[ag.NominShorter] = agent_fractions[k]/total_value
                if k == 'CuritEscrowNominShorter':
                    result[ag.CuritEscrowNominShorter] = agent_fractions[k]/total_value
        agent_fractions = result

        # Set the actual number of each agent type.
        num_bankers = int(num_agents * agent_fractions[ag.Banker]) \
                           if ag.Banker in agent_fractions else 0
        num_randomizers = int(num_agents * agent_fractions[ag.Randomizer]) \
                              if ag.Randomizer in agent_fractions else 0
        num_arbitrageurs = int(num_agents * agent_fractions[ag.Arbitrageur]) \
                               if ag.Arbitrageur in agent_fractions else 0
        num_nomin_shorters = int(num_agents * agent_fractions[ag.NominShorter]) \
                                 if ag.NominShorter in agent_fractions else 0
        num_escrow_nomin_shorters = int(num_agents * agent_fractions[ag.CuritEscrowNominShorter]) \
                                        if ag.CuritEscrowNominShorter in agent_fractions else 0

        # Keep track of the index in order to give each agent a unique identifier.
        i = 0
        for _ in range(num_bankers):
            endowment = HavvenManager.round_decimal(Dec(skewnorm.rvs(100))*init_value)
            banker = ag.Banker(i, self.havven, fiat=endowment)
            self.havven.schedule.add(banker)
            self.bankers.append(banker)
            i += 1
        for _ in range(num_randomizers):
            randomizer = ag.Randomizer(i, self.havven, fiat=init_value)
            self.havven.endow_curits(randomizer, Dec(3)*init_value)
            self.havven.schedule.add(randomizer)
            self.randomizers.append(randomizer)
            i += 1
        for _ in range(num_arbitrageurs):
            arbitrageur = ag.Arbitrageur(i, self.havven,
                                         fiat=HavvenManager.round_decimal(init_value/Dec(2)))
            self.havven.endow_curits(arbitrageur,
                                     HavvenManager.round_decimal(init_value/Dec(2)))
            self.havven.schedule.add(arbitrageur)
            self.arbitrageurs.append(arbitrageur)
            i += 1
        for _ in range(num_nomin_shorters):
            nomin_shorter = ag.NominShorter(i, self.havven,
                                            nomins=HavvenManager.round_decimal(init_value*Dec(2)))
            self.havven.schedule.add(nomin_shorter)
            self.nomin_shorters.append(nomin_shorter)
            i += 1
        for _ in range(num_escrow_nomin_shorters):
            escrow_nomin_shorter = ag.CuritEscrowNominShorter(i, self.havven,
                                                              curits=HavvenManager.round_decimal(init_value*Dec(2)))
            self.havven.schedule.add(escrow_nomin_shorter)
            self.escrow_nomin_shorters.append(escrow_nomin_shorter)
            i += 1

        speculator = ag.Speculator(i, self.havven, fiat=HavvenManager.round_decimal(init_value*Dec(5)))
        self.havven.schedule.add(speculator)
        i += 1

        central_bank = ag.CentralBank(
            i, self.havven, fiat=Dec(num_agents * init_value),
            nomin_target=Dec('1.0')
        )
        self.havven.endow_curits(central_bank,
                                 Dec(num_agents * init_value))
        self.havven.schedule.add(central_bank)
        self.others.append(central_bank)

        # Now that each agent has its initial endowment, make them remember it.
        for agent in self.havven.schedule.agents:
            agent.reset_initial_wealth()
