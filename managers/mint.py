from decimal import Decimal as Dec
from typing import Dict, Any

import agents

from .havvenmanager import HavvenManager
from .marketmanager import MarketManager
from .feemanager import FeeManager


class Mint:
    """
    Handles issuance and burning of nomins.
    """
    issuance_controller = None
    minimal_issuance_amount = Dec('0.0000001')

    def __init__(self, havven_manager: HavvenManager,
                 market_manager: MarketManager, fee_manager: FeeManager,
                 mint_settings: Dict[str, Any]) -> None:
        self.havven_manager = havven_manager
        self.market_manager = market_manager
        self.fee_manager = fee_manager
        self.copt_sensitivity_parameter: Dec = Dec(mint_settings['copt_sensitivity_parameter'])
        """How sensitive is copt/cmax to the price of nomins"""
        self.copt_flattening_parameter: int = mint_settings['copt_flattening_parameter']
        """How much buffer room is given to people close to copt"""
        if self.copt_flattening_parameter < 1 or self.copt_flattening_parameter % 2 == 0:
            raise Exception("Invalid flattening parameter, must be an odd number >= 1")
        self.copt_buffer_parameter: Dec = Dec(mint_settings['copt_buffer_parameter'])
        """cmax = buffer_parameter * copt"""
        if self.copt_buffer_parameter < 1:
            raise Exception("Invalid buffer parameter, must be >= 1")

        self.minimal_cmax: Dec = Dec(mint_settings['minimal_cmax'])
        if self.minimal_cmax <= 0:
            raise Exception("Invalid initial_cmax_copt, must be strictly > 0")

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

        self.calculate_copt_cmax()

    def add_issuance_controller(self, issuance_controller: 'agents.IssuanceController'):
        self.issuance_controller = issuance_controller

    def escrow_havvens(self, agent: "agents.MarketPlayer", value: Dec) -> bool:
        """Escrow a number of havvens for the given agent, creating a sell order
        for the created nomins"""
        if self.minimal_issuance_amount <= value <= agent.available_havvens and self.cmax > 0:
            nom_received = self.havven_manager.round_decimal(self.issued_nomins_received(value))
            agent.issued_nomins += nom_received
            self.havven_manager.issued_nomins += nom_received
            self.issuance_controller.nomins += nom_received
            self.issuance_controller.place_issuance_order(nom_received, agent)
        return False

    def issued_nomins_received(self, havvens: Dec) -> Dec:
        """The number of nomins created by escrowing a number of havvens"""
        n_i = (
            havvens *
            self.cmax *
            self.market_manager.havven_fiat_market.price /
            self.market_manager.nomin_fiat_market.price
        )
        return n_i

    def escrowed_havvens(self, agent: "agents.MarketPlayer") -> Dec:
        """
        The current number of escrowed havvens that the agent has
        Can be greater then their number of available havvens
        """
        return HavvenManager.round_decimal(
            (
                agent.issued_nomins *
                self.market_manager.nomin_fiat_market.price /
                self.market_manager.havven_fiat_market.price /
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
                self.market_manager.havven_fiat_market.price /
                self.market_manager.nomin_fiat_market.price
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
                self.market_manager.havven_fiat_market.price /
                self.market_manager.nomin_fiat_market.price

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
        Don't transfer, to avoid transfer fee (only charge the market fee)
        :param agent: the agent burning nomins
        :param value: the amount of fiat to buy nomins with
        """
        value = self.havven_manager.round_decimal(value)
        if self.minimal_issuance_amount <= value <= agent.available_fiat and value <= agent.issued_nomins and self.cmax > 0:
            agent.fiat -= value
            self.issuance_controller.fiat += value
            fee = self.market_manager.nomin_fiat_market.buyer_fee(Dec(1), value)
            agent.issued_nomins -= (value - fee)
            self.havven_manager.issued_nomins -= (value - fee)
            self.issuance_controller.place_burn_order(value, agent)
            return True
        return False

    def calculate_copt_cmax(self):
        self.copt = (self.copt_sensitivity_parameter * (
            (self.market_manager.nomin_fiat_market.price - 1) ** self.copt_flattening_parameter
        ) + 1) * self.global_collateralisation
        self.cmax = self.copt * self.copt_buffer_parameter
        if self.cmax < self.minimal_cmax:
            self.cmax = self.minimal_cmax

    @property
    def global_collateralisation(self) -> Dec:
        return (self.market_manager.nomin_fiat_market.price * self.havven_manager.issued_nomins) / \
               (self.market_manager.havven_fiat_market.price * self.havven_manager.havven_supply)
