from typing import Dict, List
from decimal import Decimal as Dec

from scipy.stats import skewnorm

import agents as ag

from .havvenmanager import HavvenManager
import model


class AgentManager:
    """Manages agent populations."""

    def __init__(self,
                 havven_model: "model.HavvenModel",
                 num_agents: int,
                 agent_fractions: Dict[str, float],
                 init_value: Dec) -> None:
        # A reference to the havven sim itself.
        self.havven_model = havven_model

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
            total = max(1, int(num_agents*agent_fractions[item]) if item in agent_fractions else 0)
            if item == 'Merchant' and total == 0:
                total = 1
            for i in range(total):
                if ag.player_names[item] == ag.Banker:
                    endowment = HavvenManager.round_decimal(Dec(skewnorm.rvs(100)) * init_value)
                    banker = ag.Banker(total_players, self.havven_model, fiat=endowment)
                    self.havven_model.schedule.add(banker)
                    self.agents[item].append(banker)
                    total_players += 1
                elif ag.player_names[item] == ag.Randomizer:
                    randomizer = ag.Randomizer(total_players, self.havven_model, fiat=init_value)
                    self.havven_model.endow_havvens(randomizer, Dec(3) * init_value)
                    self.havven_model.schedule.add(randomizer)
                    self.agents[item].append(randomizer)
                    total_players += 1
                elif ag.player_names[item] == ag.Arbitrageur:
                    arbitrageur = ag.Arbitrageur(total_players, self.havven_model,
                                                 fiat=HavvenManager.round_decimal(init_value / Dec(2)))
                    self.havven_model.endow_havvens(arbitrageur,
                                             HavvenManager.round_decimal(init_value / Dec(2)))
                    self.havven_model.schedule.add(arbitrageur)
                    self.agents[item].append(arbitrageur)
                    total_players += 1
                elif ag.player_names[item] == ag.NominShorter:
                    nomin_shorter = ag.NominShorter(total_players, self.havven_model,
                                                    nomins=HavvenManager.round_decimal(init_value * Dec(2)))
                    self.havven_model.schedule.add(nomin_shorter)
                    self.agents[item].append(nomin_shorter)
                    total_players += 1
                elif ag.player_names[item] == ag.HavvenEscrowNominShorter:
                    escrow_nomin_shorter = ag.HavvenEscrowNominShorter(
                        total_players, self.havven_model,
                        havvens=HavvenManager.round_decimal(init_value * Dec(2))
                    )
                    self.havven_model.schedule.add(escrow_nomin_shorter)
                    self.agents[item].append(escrow_nomin_shorter)
                    total_players += 1
                elif ag.player_names[item] == ag.Merchant:
                    merchant = ag.Merchant(total_players, self.havven_model, fiat=HavvenManager.round_decimal(init_value))
                    self.havven_model.schedule.add(merchant)
                    self.agents[item].append(merchant)
                    total_players += 1
                elif ag.player_names[item] == ag.Buyer:
                    buyer = ag.Buyer(total_players, self.havven_model, fiat=HavvenManager.round_decimal(init_value*Dec(2)))
                    self.havven_model.schedule.add(buyer)
                    self.agents[item].append(buyer)
                    total_players += 1
                elif ag.player_names[item] == ag.MarketMaker:
                    market_maker = ag.MarketMaker(
                        total_players,
                        self.havven_model,
                        fiat=HavvenManager.round_decimal(init_value*Dec(3))
                    )
                    self.havven_model.endow_havvens(market_maker, init_value*Dec(3))
                    self.havven_model.schedule.add(market_maker)
                    self.agents[item].append(market_maker)
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
