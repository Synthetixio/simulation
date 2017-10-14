import agents
import model

from .havvenmanager import HavvenManager
from .trademanager import TradeManager

class Mint:
    """
    Handles issuance and burning of nomins.
    """

    def __init__(self, havven_manager: HavvenManager,
                 trade_manager: TradeManager) -> None:
        self.havven_manager = havven_manager
        self.trade_manager = trade_manager

    def escrow_curits(self, agent: "agents.MarketPlayer",
                      value: float) -> bool:
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
                        value: float) -> bool:
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

    def available_escrowed_curits(self, agent: "agents.MarketPlayer") -> float:
        """
        Return the quantity of escrowed curits which is not
        locked by issued nomins. May be negative.
        """
        return agent.escrowed_curits - self.trade_manager.nomins_to_curits(agent.issued_nomins)

    def unavailable_escrowed_curits(self, agent: "agents.MarketPlayer") -> float:
        """
        Return the quantity of locked escrowed curits,
          having had nomins issued against it.
        May be greater than total escrowed curits.
        """
        return self.trade_manager.nomins_to_curits(agent.issued_nomins)

    def max_issuance_rights(self, agent: "agents.MarketPlayer") -> float:
        """The total quantity of nomins this agent has a right to issue."""
        return self.trade_manager.curits_to_nomins(agent.escrowed_curits) * \
            self.havven_manager.utilisation_ratio_max

    def issue_nomins(self, agent: "agents.MarketPlayer",
                     value: float) -> bool:
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

    def burn_nomins(self, agent: "agents.MarketPlayer",
                    value: float) -> bool:
        """Burn a positive value of issued nomins, which frees up curits."""
        if 0 <= value <= agent.nomins and value <= agent.issued_nomins:
            agent.nomins -= value
            agent.issued_nomins -= value
            self.havven_manager.nomin_supply -= value
            return True
        return False
