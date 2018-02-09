from typing import List, Dict, Any
from decimal import Decimal as Dec

import agents
from .havvenmanager import HavvenManager


class FeeManager:
    """
    Handles fee calculation.
    """

    def __init__(
            self, model_manager: HavvenManager, fee_settings: Dict[str, Any]
    ) -> None:
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
        self.fee_period: int = fee_settings['fee_distribution_period']

        self.use_transfer_fee = fee_settings['transfer_fee']
        if self.use_transfer_fee:
            # Multiplicative transfer fee rates
            self.nomin_transfer_fee_rate = Dec(fee_settings['transfer_fee_settings']['nomin_fee_level'])
            # these two should probably be 0...
            self.havven_transfer_fee_rate = Dec(fee_settings['transfer_fee_settings']['havven_fee_level'])
            self.fiat_transfer_fee_rate = Dec(fee_settings['transfer_fee_settings']['fiat_fee_level'])

        # Multiplicative issuance fee rates
        # only the burning fee rate is actually used, as a fee is
        # charged on the market buy/sell of nomins for issuance/burning
        # this will need to be implemented if an extra fee will be added...
        self.issuance_fee_rate = Dec(fee_settings['nomin_issuance_fee'])
        self.burning_fee_rate = Dec(fee_settings['nomin_burning_fee'])

        self.use_hedging_fee = fee_settings['hedging_fee']
        if self.use_hedging_fee:
            self.nomin_hedge_fee_rate = Dec(fee_settings['hedging_fee_settings']['nomin_fee_level'])
            # these two should always be 0...
            self.havven_hedge_fee_rate = Dec(fee_settings['hedging_fee_settings']['havven_fee_level'])
            self.fiat_hedge_fee_rate = Dec(fee_settings['hedging_fee_settings']['fiat_fee_level'])
            self.hedge_length = fee_settings['hedging_fee_settings']['hedge_length']

        self.fees_distributed = Dec(0)

    @property
    def nomin_fee_rate(self) -> Dec:
        if self.use_transfer_fee:
            return self.nomin_transfer_fee_rate
        return Dec(0)

    @property
    def havven_fee_rate(self) -> Dec:
        if self.use_transfer_fee:
            return self.havven_transfer_fee_rate
        return Dec(0)

    @property
    def fiat_fee_rate(self) -> Dec:
        if self.use_transfer_fee:
            return self.fiat_transfer_fee_rate
        return Dec(0)

    def collect_hedge_fees(self, actor):
        if self.use_hedging_fee:
            nom_fee = self.nomin_hedge_fee_rate * actor.nomins / self.hedge_length
            actor.nomins -= nom_fee
            self.model_manager.nomins += nom_fee
            hav_fee = self.havven_hedge_fee_rate * actor.havvens / self.hedge_length
            actor.havvens -= hav_fee
            self.model_manager.nomins += hav_fee
            fiat_fee = self.fiat_hedge_fee_rate * actor.fiat / self.hedge_length
            actor.fiat -= fiat_fee
            self.model_manager.nomins += fiat_fee

    def transferred_fiat_received(self, quantity: Dec) -> Dec:
        """
        Returns the fiat received by the recipient if a given quantity (with fee)
          is transferred.
        A user can only transfer less than their total balance when fees
          are taken into account.
        """
        if not self.use_transfer_fee:
            return quantity
        return HavvenManager.round_decimal(quantity / (Dec(1) + self.fiat_fee_rate))

    def transferred_havvens_received(self, quantity: Dec) -> Dec:
        """
        Returns the havvens received by the recipient if a given quantity (with fee)
          is transferred.
        A user can only transfer less than their total balance when fees
          are taken into account.
        """
        if not self.use_transfer_fee:
            return quantity
        return HavvenManager.round_decimal(quantity / (Dec(1) + self.havven_fee_rate))

    def transferred_nomins_received(self, quantity: Dec) -> Dec:
        """
        Returns the nomins received by the recipient if a given quantity (with fee)
          is transferred.
        A user can only transfer less than their total balance when fees
          are taken into account.
        """
        if not self.use_transfer_fee:
            return quantity
        return HavvenManager.round_decimal(quantity / (Dec(1) + self.nomin_fee_rate))

    def transferred_fiat_fee(self, quantity: Dec) -> Dec:
        """
        Return the fee charged for transferring a quantity of fiat.
        """
        if not self.use_transfer_fee:
            return Dec(0)
        return HavvenManager.round_decimal(quantity * self.fiat_fee_rate)

    def transferred_havvens_fee(self, quantity: Dec) -> Dec:
        """
        Return the fee charged for transferring a quantity of havvens.
        """
        if not self.use_transfer_fee:
            return Dec(0)
        return HavvenManager.round_decimal(quantity * self.havven_fee_rate)

    def transferred_nomins_fee(self, quantity: Dec) -> Dec:
        """
        Return the fee charged for transferring a quantity of nomins.
        """
        if not self.use_transfer_fee:
            return Dec(0)
        return HavvenManager.round_decimal(quantity * self.nomin_fee_rate)

    def distribute_fees(
            self, schedule_agents: List["agents.MarketPlayer"], copt: Dec, cmax: Dec
    ) -> None:
        """
        Distribute currently held nomins to holders of havvens.
        """
        # Different fee modes:
        #  * distributed by held havvens
        # TODO: * distribute by escrowed havvens
        # TODO: * distribute by issued nomins
        # TODO: * distribute by motility

        pre_nomins = self.model_manager.nomins

        # calculate alphabase

        abase = 0

        for agent in schedule_agents:
            ci = agent.collateralisation
            if ci <= copt:
                fee_mult = ci / copt
            elif copt < ci <= cmax:
                fee_mult = (cmax - ci) / (cmax - copt)
            else:
                fee_mult = 0
            abase += agent.havvens * fee_mult

        if abase <= 0:
            print("Skipping fee distribution, no ci is in the 0->cmax range")
            return

        for agent in schedule_agents:
            if self.model_manager.nomins < 0:
                raise Exception("Model manager has less than 0 nomins when distributing fees")
            ci = agent.collateralisation
            if ci <= copt:
                fee_mult = ci / copt
            elif copt < ci <= cmax:
                fee_mult = (cmax - ci) / (cmax - copt)
            else:
                fee_mult = 0

            qty = (agent.havvens * fee_mult / abase * pre_nomins) * Dec('0.995')

            agent.nomins += qty
            self.model_manager.nomins -= qty
            self.fees_distributed += qty
