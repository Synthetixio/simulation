from decimal import Decimal as Dec
from typing import Dict, Any

import agents

from .havvenmanager import HavvenManager
from .marketmanager import MarketManager


class Mint:
    """
    Handles issuance and burning of nomins.
    """
    def __init__(self, havven_manager: HavvenManager,
                 market_manager: MarketManager, mint_settings: Dict[str, Any]) -> None:
        self.havven_manager = havven_manager
        self.market_manager = market_manager
        self.copt_sensitivity_parameter: Dec = mint_settings['copt_sensitivity_parameter']
        """How sensitive is copt/cmax to the price of nomins"""
        self.copt_flattening_parameter: int = mint_settings['copt_flattening_parameter']
        """How much buffer room is given to people close to copt"""
        if self.copt_flattening_parameter < 1 or self.copt_flattening_parameter % 2 == 0:
            raise Exception("Invalid flattening parameter, must be an odd number >= 1")
        self.copt_buffer_parameter: Dec = mint_settings['copt_buffer_parameter']
        """cmax = buffer_parameter * copt"""
        if self.copt_buffer_parameter < 1:
            raise Exception("Invalid buffer parameter, must be >= 1")

        self.non_discretionary_issuance: bool = mint_settings['non_discretionary_issuance']
        """Do nomins get sold by the system, giving players fiat"""
        if not self.non_discretionary_issuance:
            raise Exception("""Discretionary issuance has been removed for the time being
            This option exists for the time being if the logic will be reimplemented.
            Older versions of the model (PR #107 and back) are all discretionary""")

        self.non_discretionary_cap_buffer: Dec = mint_settings['non_discretionary_cap_buffer']

        self.copt: Dec = Dec(-1)
        """Optimal collateralisation ratio"""
        self.cmax: Dec = Dec(-1)
        """Maximal collateralisation value"""

    def escrow_havvens(self, agent: "agents.MarketPlayer", value: Dec) -> bool:
        """Escrow a number of havvens for the given agent, creating a sell order
        for the created nomins"""
        if 0 <= value <= agent.available_havvens:
            nom_received = self.issued_nomins_received(value)
            agent.issued_nomins += nom_received
            # TODO: sell nomins
        return False

    def issued_nomins_received(self, havvens: Dec) -> Dec:
        """The number of nomins created by escrowing a number of havvens"""
        n_i = (
            havvens *
            self.cmax *
            self.market_manager.havven_nomin_market.price
        )
        return n_i

    def escrowed_havvens(self, agent: "agents.MarketPlayer") -> Dec:
        """
        The current number of escrowed havvens that the agent has
        Can be greater then their number of available havvens
        """
        return HavvenManager.round_decimal(
            (
                agent.issued_nomins /
                self.market_manager.havven_nomin_market.price /
                self.cmax
            )
        )

    def max_issuance_rights(self, agent: "agents.MarketPlayer") -> Dec:
        """
        The total quantity of nomins this agent has a right to issue.
        """
        return HavvenManager.round_decimal(
            (
                agent.available_havvens *
                self.cmax *
                self.market_manager.havven_nomin_market.price
            )
        )

    def optimal_issuance_rights(self, agent: "agents.MarketPlayer") -> Dec:
        """
        The total quantity of nomins this agent should issue to get to Copt.
        """
        return HavvenManager.round_decimal(
            (
                agent.available_havvens *
                self.copt *
                self.market_manager.havven_nomin_market.price
            )
        )

    def remaining_issuance_rights(self, agent: "agents.MarketPlayer") -> Dec:
        """
        Return the remaining quantity of tokens this agent can issued on the back of their
          escrowed havvens. May be negative.
        """
        return self.max_issuance_rights(agent) - agent.issued_nomins

    def free_havvens(self, agent: "agents.MarketPlayer", value: Dec) -> bool:
        """
        Buy a positive value of nomins (using fiat) to burn, which frees up havvens.
        """
        if 0 <= value <= agent.available_fiat and value <= agent.issued_nomins:
            agent.nomins -= value
            agent.issued_nomins -= value
            self.havven_manager.nomin_supply -= value
            return True
        return False

    def calculate_copt_cmax(self):
        self.copt = (self.copt_sensitivity_parameter * (
            (self.market_manager.nomin_fiat_market.price - 1)**self.copt_flattening_parameter
            ) + 1) * self.global_collateralisation
        self.cmax = self.copt*self.copt_buffer_parameter

    @property
    def global_collateralisation(self) -> Dec:
        return (self.market_manager.nomin_fiat_market.price * self.havven_manager.nomin_supply) / \
               (self.market_manager.havven_fiat_market.price * self.havven_manager.havven_supply)
