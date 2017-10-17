from decimal import Decimal as Dec

import agents

from .havvenmanager import HavvenManager
from .marketmanager import MarketManager


class Mint:
    """
    Handles issuance and burning of nomins.
    """

    def __init__(self, havven_manager: HavvenManager,
                 market_manager: MarketManager) -> None:
        self.havven_manager = havven_manager
        self.market_manager = market_manager

    def escrow_curits(self, agent: "agents.MarketPlayer",
                      value: Dec) -> bool:
        """
        Escrow a positive value of curits in order to be able to issue
        nomins against them.
        """
        if agent.curits >= value >= 0:
            agent.curits -= value
            agent.escrowed_curits += value
            self.havven_manager.escrowed_curits += value
            return True
        return False

    def unescrow_curits(self, agent: "agents.MarketPlayer",
                        value: Dec) -> bool:
        """
        Unescrow a quantity of curits, if there are not too many
        issued nomins locking it.
        """
        if 0 <= value <= self.available_escrowed_curits(agent):
            agent.curits += value
            agent.escrowed_curits -= value
            self.havven_manager.escrowed_curits -= value
            return True
        return False
    
    ### FIXME TODO ###
    ### THIS LOGIC IS BROKEN. UTILISATION RATIO NOT TAKEN INTO ACCOUNT AT EVERY LOCATION ###
    ### ALSO NEED TO ENSURE THAT NOMINS ARE ACTUALLY PROPERLY-ISSUABLE ###

    def available_escrowed_curits(self, agent: "agents.MarketPlayer") -> Dec:
        """
        Return the quantity of escrowed curits which is not
        locked by issued nomins. May be negative.
        """
        return agent.escrowed_curits - self.unavailable_escrowed_curits(agent)

    def unavailable_escrowed_curits(self, agent: "agents.MarketPlayer") -> Dec:
        """
        Return the quantity of locked escrowed curits,
          having had nomins issued against it.
        May be greater than total escrowed curits.
        """
        return self.market_manager.nomins_to_curits(agent.issued_nomins)

    def max_issuance_rights(self, agent: "agents.MarketPlayer") -> Dec:
        """
        The total quantity of nomins this agent has a right to issue.
        """
        return self.market_manager.curits_to_nomins(agent.escrowed_curits) * \
            self.havven_manager.utilisation_ratio_max

    def remaining_issuance_rights(self, agent: "agents.MarketPlayer") -> Dec:
        """
        Return the remaining quantity of tokens this agent can issued on the back of their
          escrowed curits. May be negative.
        """
        return self.market_manager.curits_to_nomins(self.available_escrowed_curits(agent))

    def issue_nomins(self, agent: "agents.MarketPlayer", value: Dec) -> bool:
        """
        Issue a positive value of nomins against currently escrowed curits,
          up to the utilisation ratio maximum.
        """
        remaining = self.max_issuance_rights(agent) - agent.issued_nomins
        if 0 <= value <= remaining:
            agent.issued_nomins += value
            agent.nomins += value
            self.havven_manager.nomin_supply += value
            return True
        return False

    def burn_nomins(self, agent: "agents.MarketPlayer", value: Dec) -> bool:
        """
        Burn a positive value of issued nomins, which frees up curits.
        """
        if 0 <= value <= agent.nomins and value <= agent.issued_nomins:
            agent.nomins -= value
            agent.issued_nomins -= value
            self.havven_manager.nomin_supply -= value
            return True
        return False
