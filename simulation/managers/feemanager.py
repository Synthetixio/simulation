from typing import List

import agents 
from .havvenmanager import HavvenManager

class FeeManager:
    """
    Handles fee calculation.
    """

    def __init__(self, model_manager: HavvenManager) -> None:

        self.model_manager = model_manager

        # Fees are distributed at regular intervals
        self.fee_period: int = 50

        # Multiplicative transfer fee rates
        self.nom_fee_rate: float = 0.005
        self.cur_fee_rate: float = 0.005
        self.fiat_fee_rate: float = 0.005

        # Multiplicative issuance fee rates
        self.issuance_fee_rate: float = 0.0
        self.redemption_fee_rate: float = 0.0

        self.fees_distributed: float = 0.0

    def transferred_fiat_received(self, quantity: float) -> float:
        """
        Returns the fiat received by the recipient if a given quantity
          is transferred.
        A user can only transfer less than their total balance when fees
          are taken into account.
        """
        return quantity / (1 + self.fiat_fee_rate)

    def transferred_curits_received(self, quantity: float) -> float:
        """
        Returns the curits received by the recipient if a given quantity
          is transferred.
        A user can only transfer less than their total balance when fees
          are taken into account.
        """
        return quantity / (1 + self.cur_fee_rate)

    def transferred_nomins_received(self, quantity: float) -> float:
        """
        Returns the nomins received by the recipient if a given quantity
          is transferred.
        A user can only transfer less than their total balance when fees
          are taken into account.
        """
        return quantity / (1 + self.nom_fee_rate)

    def transferred_fiat_fee(self, quantity: float) -> float:
        """
        Return the fee charged for transferring a quantity of fiat.
        """
        return quantity * self.fiat_fee_rate

    def transferred_curits_fee(self, quantity: float) -> float:
        """
        Return the fee charged for transferring a quantity of curits.
        """
        return quantity * self.cur_fee_rate

    def transferred_nomins_fee(self, quantity: float) -> float:
        """
        Return the fee charged for transferring a quantity of nomins.
        """
        return quantity * self.nom_fee_rate

    def distribute_fees(self, schedule_agents: List["agents.MarketPlayer"]) -> None:
        """
        Distribute currently held nomins to holders of curits.
        """
        # Different fee modes:
        #  * distributed by held curits
        # TODO: * distribute by escrowed curits
        # TODO: * distribute by issued nomins
        # TODO: * distribute by motility

        pre_nomins = self.model_manager.nomins
        for agent in schedule_agents:
            if self.model_manager.nomins <= 0.0:
                break
            qty = min(pre_nomins * agent.issued_nomins / self.model_manager.nomin_supply,
                      self.model_manager.nomins)
            agent.nomins += qty
            self.model_manager.nomins -= qty
            self.fees_distributed += qty
