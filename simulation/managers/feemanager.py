from typing import List
from decimal import Decimal as Dec
from random import shuffle

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
        self.nom_fee_rate: Dec = Dec('0.005')
        self.cur_fee_rate: Dec = Dec('0.005')
        self.fiat_fee_rate: Dec = Dec('0.005')

        # Multiplicative issuance fee rates
        self.issuance_fee_rate: Dec = Dec('0.0')
        self.redemption_fee_rate: Dec = Dec('0.0')

        self.fees_distributed: Dec = Dec(0)

    def transferred_fiat_received(self, quantity: Dec) -> Dec:
        """
        Returns the fiat received by the recipient if a given quantity(with fee)
          is transferred.
        A user can only transfer less than their total balance when fees
          are taken into account.
        """
        return HavvenManager.round_decimal(quantity / (Dec(1) + self.fiat_fee_rate))

    def transferred_curits_received(self, quantity: Dec) -> Dec:
        """
        Returns the curits received by the recipient if a given quantity(with fee)
          is transferred.
        A user can only transfer less than their total balance when fees
          are taken into account.
        """
        return HavvenManager.round_decimal(quantity / (Dec(1) + self.cur_fee_rate))

    def transferred_nomins_received(self, quantity: Dec) -> Dec:
        """
        Returns the nomins received by the recipient if a given quantity(with fee)
          is transferred.
        A user can only transfer less than their total balance when fees
          are taken into account.
        """
        return HavvenManager.round_decimal(quantity / (Dec(1) + self.nom_fee_rate))

    def transferred_fiat_fee(self, quantity: Dec) -> Dec:
        """
        Return the fee charged for transferring a quantity of fiat.
        """
        return HavvenManager.round_decimal(quantity * self.fiat_fee_rate)

    def transferred_curits_fee(self, quantity: Dec) -> Dec:
        """
        Return the fee charged for transferring a quantity of curits.
        """
        return HavvenManager.round_decimal(quantity * self.cur_fee_rate)

    def transferred_nomins_fee(self, quantity: Dec) -> Dec:
        """
        Return the fee charged for transferring a quantity of nomins.
        """
        return HavvenManager.round_decimal(quantity * self.nom_fee_rate)

    def distribute_fees(self, schedule_agents: List["agents.MarketPlayer"]) -> None:
        """
        Distribute currently held nomins to holders of curits.
        """
        # Different fee modes:
        #  * distributed by held curits
        # TODO: * distribute by escrowed curits
        # TODO: * distribute by issued nomins
        # TODO: * distribute by motility

        # reward in random order in case there's
        # some ordering bias I'm missing.
        shuffled_agents = list(schedule_agents)
        shuffle(shuffled_agents)

        pre_nomins = self.model_manager.nomins
        supply = self.model_manager.nomin_supply
        for agent in shuffled_agents:
            if self.model_manager.nomins <= 0:
                break
            qty = min(HavvenManager.round_decimal(pre_nomins * agent.issued_nomins / supply),
                      self.model_manager.nomins)
            agent.nomins += qty
            self.model_manager.nomins -= qty
            self.fees_distributed += qty
