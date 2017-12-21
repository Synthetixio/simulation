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
        self.copt_flattening_parameter: int = mint_settings['copt_flattening_parameter']
        if self.copt_flattening_parameter < 1 or self.copt_flattening_parameter % 2 == 0:
            raise Exception("Invalid flattening parameter, must be an odd number >= 1.")
        self.copt_buffer_parameter: Dec = mint_settings['copt_buffer_parameter']

    def escrow_havvens(self, agent: "agents.MarketPlayer",
                      value: Dec) -> bool:
        """
        Escrow a positive value of havvens in order to be able to issue
        nomins against them.
        """
        if agent.available_havvens >= value >= 0:
            agent.havvens -= value
            agent.escrowed_havvens += value
            self.havven_manager.escrowed_havvens += value
            return True
        return False

    def unescrow_havvens(self, agent: "agents.MarketPlayer",
                        value: Dec) -> bool:
        """
        Unescrow a quantity of havvens, if there are not too many
        issued nomins locking it.
        """
        if 0 <= value <= self.available_escrowed_havvens(agent):
            agent.havvens += value
            agent.escrowed_havvens -= value
            self.havven_manager.escrowed_havvens -= value
            return True
        return False

    ### FIXME TODO ###
    ### THIS LOGIC IS BROKEN. UTILISATION RATIO NOT TAKEN INTO ACCOUNT AT EVERY LOCATION ###
    ### ALSO NEED TO ENSURE THAT NOMINS ARE ACTUALLY PROPERLY-ISSUABLE ###

    def available_escrowed_havvens(self, agent: "agents.MarketPlayer") -> Dec:
        """
        Return the quantity of escrowed havvens which is not
        locked by issued nomins. May be negative.
        """
        return agent.escrowed_havvens - self.unavailable_escrowed_havvens(agent)

    def unavailable_escrowed_havvens(self, agent: "agents.MarketPlayer") -> Dec:
        """
        Return the quantity of locked escrowed havvens,
          having had nomins issued against it.
        May be greater than total escrowed havvens.
        """
        return self.market_manager.nomins_to_havvens(agent.issued_nomins)

    def max_issuance_rights(self, agent: "agents.MarketPlayer") -> Dec:
        """
        The total quantity of nomins this agent has a right to issue.
        """
        return HavvenManager.round_decimal(self.market_manager.havvens_to_nomins(agent.escrowed_havvens) * \
            self.havven_manager.utilisation_ratio_max)

    def remaining_issuance_rights(self, agent: "agents.MarketPlayer") -> Dec:
        """
        Return the remaining quantity of tokens this agent can issued on the back of their
          escrowed havvens. May be negative.
        """
        return self.max_issuance_rights(agent) - agent.issued_nomins

    def issue_nomins(self, agent: "agents.MarketPlayer", value: Dec) -> bool:
        """
        Issue a positive value of nomins against currently escrowed havvens,
          up to the utilisation ratio maximum.
        """
        remaining = self.remaining_issuance_rights(agent)
        if 0 <= value <= remaining:
            agent.issued_nomins += value
            agent.nomins += value
            self.havven_manager.nomin_supply += value
            return True
        return False

    def burn_nomins(self, agent: "agents.MarketPlayer", value: Dec) -> bool:
        """
        Burn a positive value of issued nomins, which frees up havvens.
        """
        if 0 <= value <= agent.available_nomins and value <= agent.issued_nomins:
            agent.nomins -= value
            agent.issued_nomins -= value
            self.havven_manager.nomin_supply -= value
            return True
        return False
