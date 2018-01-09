from typing import List, Dict, Any
from decimal import Decimal as Dec
from random import shuffle

import agents 
from .havvenmanager import HavvenManager


class FeeManager:
    """
    Handles fee calculation.
    """

    def __init__(self, model_manager: HavvenManager, fee_settings: Dict[str, Any]) -> None:
        """
        :param model_manager: a model_manager object
        :param fee_settings: The settings for fees:
         - fee_period: how often fees are paid out to havven holders
         - stable_nomin_fee_level: the fee rate for nomins
         - stable_havven_fee_level: the fee rate for havvens
         - stable_fiat_fee_level: the fee rate for fiat
         - stable_nomin_issuance_fee: the fee rate for nomin issuance
         - stable_nomin_redemption_fee: the fee rate for nomin redemption
        """
        self.model_manager = model_manager

        # Fees are distributed at regular intervals
        self.fee_period: int = fee_settings['fee_period']

        # Multiplicative transfer fee rates
        self.nomin_fee_rate = Dec(fee_settings['stable_nomin_fee_level'])
        self.havven_fee_rate = Dec(fee_settings['stable_havven_fee_level'])
        self.fiat_fee_rate = Dec(fee_settings['stable_fiat_fee_level'])

        # Multiplicative issuance fee rates
        self.issuance_fee_rate = Dec(fee_settings['stable_nomin_issuance_fee'])
        self.redemption_fee_rate = Dec(fee_settings['stable_nomin_redemption_fee'])

        self.fees_distributed = Dec(0)

    def transferred_fiat_received(self, quantity: Dec) -> Dec:
        """
        Returns the fiat received by the recipient if a given quantity (with fee)
          is transferred.
        A user can only transfer less than their total balance when fees
          are taken into account.
        """
        return HavvenManager.round_decimal(quantity / (Dec(1) + self.fiat_fee_rate))

    def transferred_havvens_received(self, quantity: Dec) -> Dec:
        """
        Returns the havvens received by the recipient if a given quantity (with fee)
          is transferred.
        A user can only transfer less than their total balance when fees
          are taken into account.
        """
        return HavvenManager.round_decimal(quantity / (Dec(1) + self.havven_fee_rate))

    def transferred_nomins_received(self, quantity: Dec) -> Dec:
        """
        Returns the nomins received by the recipient if a given quantity (with fee)
          is transferred.
        A user can only transfer less than their total balance when fees
          are taken into account.
        """
        return HavvenManager.round_decimal(quantity / (Dec(1) + self.nomin_fee_rate))

    def transferred_fiat_fee(self, quantity: Dec) -> Dec:
        """
        Return the fee charged for transferring a quantity of fiat.
        """
        return HavvenManager.round_decimal(quantity * self.fiat_fee_rate)

    def transferred_havvens_fee(self, quantity: Dec) -> Dec:
        """
        Return the fee charged for transferring a quantity of havvens.
        """
        return HavvenManager.round_decimal(quantity * self.havven_fee_rate)

    def transferred_nomins_fee(self, quantity: Dec) -> Dec:
        """
        Return the fee charged for transferring a quantity of nomins.
        """
        return HavvenManager.round_decimal(quantity * self.nomin_fee_rate)

    def distribute_fees(self, schedule_agents: List["agents.MarketPlayer"]) -> None:
        """
        Distribute currently held nomins to holders of havvens.
        """
        # Different fee modes:
        #  * distributed by held havvens
        # TODO: * distribute by escrowed havvens
        # TODO: * distribute by issued nomins
        # TODO: * distribute by motility

        # reward in random order in case there's
        # some ordering bias I'm missing.
        shuffled_agents = list(schedule_agents)
        shuffle(shuffled_agents)

        pre_nomins = self.model_manager.nomins
        for agent in shuffled_agents:
            if self.model_manager.nomins <= 0:
                break
            qty = min(HavvenManager.round_decimal(pre_nomins * agent.issued_nomins),
                      self.model_manager.nomins)
            agent.nomins += qty
            self.model_manager.nomins -= qty
            self.fees_distributed += qty
