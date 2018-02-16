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

        self.discretionary_burning = mint_settings['discretionary_burning']

        self.fixed_cmax = mint_settings['fixed_cmax']

        if self.fixed_cmax:
            self.fixed_cmax_value = mint_settings['fixed_cmax_settings']["fixed_cmax_value"]
            self.fixed_cmax_moves_up = mint_settings['fixed_cmax_settings']["fixed_cmax_moves_up"]

        self.minimal_cmax: Dec = Dec(mint_settings['minimal_cmax'])

        self.use_copt = mint_settings['use_copt']

        if self.use_copt:
            self.copt_sensitivity_parameter: Dec = Dec(mint_settings['copt_settings']['copt_sensitivity_parameter'])
            """How sensitive is copt/cmax to the price of nomins"""

            self.copt_flattening_parameter: int = mint_settings['copt_settings']['copt_flattening_parameter']
            """How much buffer room is given to people close to copt"""
            if self.copt_flattening_parameter < 1 or self.copt_flattening_parameter % 2 == 0:
                raise Exception("Invalid flattening parameter, must be an odd number >= 1")

            self.copt_buffer_parameter: Dec = Dec(mint_settings['copt_settings']['copt_buffer_parameter'])
            """cmax = buffer_parameter * copt"""
            if self.copt_buffer_parameter < 1:
                raise Exception("Invalid buffer parameter, must be >= 1")

        self.non_discretionary_cap_buffer: Dec = mint_settings['non_discretionary_cap_buffer']

        self.copt: Dec = Dec(-1)
        """Optimal collateralisation ratio"""
        self.cmax: Dec = Dec(-1)
        """Maximal collateralisation value"""

    def add_issuance_controller(self, issuance_controller: 'agents.IssuanceController'):
        self.issuance_controller = issuance_controller

    def escrow_havvens(self, agent: "agents.MarketPlayer", value: Dec) -> bool:
        """Escrow a number of havvens for the given agent, creating a sell order
        for the created nomins"""
        value = self.havven_manager.round_decimal(value)
        if self.minimal_issuance_amount <= value <= agent.available_havvens and self.cmax > 0:
            nom_received = self.havven_manager.round_decimal(self.issued_nomins_received(value))
            print("should receive", nom_received)
            if nom_received <= Dec(0):
                return False
            agent.issued_nomins += nom_received
            self.havven_manager.issued_nomins += nom_received
            self.issuance_controller.nomins += nom_received
            self.issuance_controller.place_issuance_order(nom_received, agent)
            return True
        return False

    def issued_nomins_received(self, havvens: Dec) -> Dec:
        """The number of nomins created by escrowing a number of havvens"""
        return (
            havvens *
            self.cmax *
            self.intrinsic_havven_value /
            self.market_manager.nomin_fiat_market.price
        )

    def escrowed_havvens(self, agent: "agents.MarketPlayer") -> Dec:
        """
        The current number of escrowed havvens that the agent has
        Can be greater then their number of available havvens
        """
        return HavvenManager.round_decimal(
            (
                agent.issued_nomins *
                self.market_manager.nomin_fiat_market.price /
                self.intrinsic_havven_value /
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
                self.intrinsic_havven_value /
                self.market_manager.nomin_fiat_market.price
            )
        )

    def optimal_issuance_rights(self, agent: "agents.MarketPlayer") -> Dec:
        """
        The total quantity of nomins this agent should issue to get to Copt.
        """
        if self.use_copt:
            return HavvenManager.round_decimal(
                (
                    agent.available_havvens *
                    self.copt *
                    self.intrinsic_havven_value /
                    self.market_manager.nomin_fiat_market.price
                )
            )
        raise Exception("use_copt is false", agent, "tried to call optimal_issuance_rights")

    def havvens_off_optimal(self, agent: "agents.MarketPlayer") -> Dec:
        """
        How many havvens above or below is an agent to be at copt
        """
        if self.use_copt:
            current_escrowed = self.escrowed_havvens(agent)
            unescrowed = agent.havvens - current_escrowed
            debt = 0
            if unescrowed < 0:  # i.e. in debt
                debt = unescrowed

            goal_escrowed = (self.copt / self.cmax) * agent.havvens

            return current_escrowed - goal_escrowed + debt
        raise Exception("use_copt is false", agent, "tried to call havvens_off_optimal")

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
        if self.minimal_issuance_amount <= value <= agent.available_fiat and \
                value <= (agent.issued_nomins + agent.burning_fiat) and self.cmax > 0:
            agent.fiat -= value
            agent.burning_fiat += value
            self.issuance_controller.fiat += value
            self.issuance_controller.place_burn_order(value, agent)
            return True
        return False

    def burn_nomins(self, agent: "agents.MarketPlayer", value: Dec) -> None:
        burn_fee = value*self.fee_manager.burning_fee_rate
        if value <= agent.available_nomins and value-burn_fee <= (agent.issued_nomins + agent.burning_fiat):
            agent.nomins -= value
            agent.issued_nomins -= value-burn_fee
            self.havven_manager.issued_nomins -= (value - burn_fee)

    def calculate_copt_cmax(self):
        if self.use_copt:
            self.copt = (self.copt_sensitivity_parameter * (
                (self.market_manager.nomin_fiat_market.price - 1) ** self.copt_flattening_parameter
            ) + 1) * self.global_collateralisation

        if self.fixed_cmax:
            self.cmax = self.minimal_cmax
            if self.use_copt and self.fixed_cmax_moves_up:
                if self.cmax < self.copt * self.copt_buffer_parameter:
                    self.cmax = self.copt * self.copt_buffer_parameter
        else:
            self.cmax = self.copt * self.copt_buffer_parameter
            if self.cmax < self.minimal_cmax:
                self.cmax = self.minimal_cmax

    @property
    def global_collateralisation(self) -> Dec:
        return self.global_nomin_value / self.global_havven_value

    @property
    def intrinsic_havven_value(self) -> Dec:
        fees = self.fee_manager.last_fees_collected
        return max(Dec(0.1), fees/(self.havven_manager.havven_supply * Dec('0.0001')))

    @property
    def global_nomin_value(self) -> Dec:
        return self.havven_manager.issued_nomins * self.market_manager.nomin_fiat_market.price

    @property
    def global_havven_value(self) -> Dec:
        return self.havven_manager.active_havvens * (self.market_manager.havven_fiat_market.price + self.intrinsic_havven_value)
