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
        self.agents: Dict[str, List[ag.MarketPlayer]] = {
            name: [] for name in ag.player_names
        }
        self.agents["others"] = []

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
            total = int(num_agents*agent_fractions[item]) if item in agent_fractions else 0
            if item == 'Merchant' and total == 0:
                total = 1
            for i in range(total):
                if ag.player_names[item] == ag.Banker:
                    endowment = HavvenManager.round_decimal(Dec(skewnorm.rvs(100)) * init_value)
                    banker = ag.Banker(total_players, self.havven, fiat=endowment)
                    self.havven.schedule.add(banker)
                    self.agents[item].append(banker)
                    total_players += 1
                elif ag.player_names[item] == ag.Randomizer:
                    randomizer = ag.Randomizer(total_players, self.havven, fiat=init_value)
                    self.havven.endow_curits(randomizer, Dec(3) * init_value)
                    self.havven.schedule.add(randomizer)
                    self.agents[item].append(randomizer)
                    total_players += 1
                elif ag.player_names[item] == ag.Arbitrageur:
                    arbitrageur = ag.Arbitrageur(total_players, self.havven,
                                                 fiat=HavvenManager.round_decimal(init_value / Dec(2)))
                    self.havven.endow_curits(arbitrageur,
                                             HavvenManager.round_decimal(init_value / Dec(2)))
                    self.havven.schedule.add(arbitrageur)
                    self.agents[item].append(arbitrageur)
                    total_players += 1
                elif ag.player_names[item] == ag.NominShorter:
                    nomin_shorter = ag.NominShorter(total_players, self.havven,
                                                    curits=HavvenManager.round_decimal(init_value * Dec(3)))
                    self.havven.schedule.add(nomin_shorter)
                    self.agents[item].append(nomin_shorter)
                    total_players += 1
                elif ag.player_names[item] == ag.CuritEscrowNominShorter:
                    escrow_nomin_shorter = ag.CuritEscrowNominShorter(
                        total_players, self.havven,
                    )
                    self.havven.endow_curits(escrow_nomin_shorter, HavvenManager.round_decimal(init_value * Dec(2)))
                    self.havven.schedule.add(escrow_nomin_shorter)
                    self.agents[item].append(escrow_nomin_shorter)
                    total_players += 1
                elif ag.player_names[item] == ag.Speculator:
                    speculator = ag.Speculator(total_players, self.havven)
                    if speculator.primary_currency == "fiat":
                        speculator.fiat = HavvenManager.round_decimal(init_value*Dec(3))
                    elif speculator.primary_currency == "nomins":
                        speculator.nomins = 0
                    elif speculator.primary_currency == "curits":
                        self.havven.endow_curits(speculator, HavvenManager.round_decimal(init_value * Dec(3)))
                    self.havven.schedule.add(speculator)
                    total_players += 1
                elif ag.player_names[item] == ag.Merchant:
                    merchant = ag.Merchant(total_players, self.havven, fiat=HavvenManager.round_decimal(init_value))
                    self.havven.schedule.add(merchant)
                    self.agents[item].append(merchant)
                    total_players += 1
                elif ag.player_names[item] == ag.Buyer:
                    buyer = ag.Buyer(total_players, self.havven, fiat=HavvenManager.round_decimal(init_value*Dec(2)))
                    self.havven.schedule.add(buyer)
                    self.agents[item].append(buyer)
                    total_players += 1

        # central_bank = ag.CentralBank(
        #     total_players, self.havven, fiat=Dec(num_agents * init_value),
        #     nomin_target=Dec('1.0')
        # )
        # self.havven.endow_curits(central_bank,
        #                          Dec(num_agents * init_value))
        # self.havven.schedule.add(central_bank)
        # self.agents["others"].append(central_bank)

        # Now that each agent has its initial endowment, make them remember it.
        for agent in self.havven.schedule.agents:
            agent.reset_initial_wealth()

    def add(self, agent):
        self.havven.schedule.add(agent)
        for name, item in ag.player_names.items():
            if type(agent) == item:
                self.agents[name].append(agent)
                return
        else:
            self.agents['others'].append(agent)
