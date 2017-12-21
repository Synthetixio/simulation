from decimal import getcontext, ROUND_HALF_UP
from decimal import Decimal as Dec
from typing import Dict, Any


class HavvenManager:
    """
    Class to hold the Havven model's variables
    """

    currency_precision = 8
    """
    Number of decimal places for currency precision.
    The decimal context precision should be significantly higher than this.
    """

    def __init__(self, continuous_order_matching: bool, havven_settings: Dict[str, Any]) -> None:
        """
        :param continuous_order_matching:
        :param havven_settings:
         - havven_supply: the total amount of havvens in the system
         - nomin_supply: the amount of nomins the havven system begins with
         - rolling_avg_time_window: the amount of steps to consider when calculating the
         rolling price average
         - use_volume_weighted_avg: whether to use volume in calculating the rolling price average
        """
        # Set the decimal rounding mode
        getcontext().rounding = ROUND_HALF_UP

        # Initiate Time
        self.time: int = 0

        # Utilisation Ratio maximum (between 0 and 1)
        self.utilisation_ratio_max: Dec = Dec(0.2)  # TODO: remove this

        # If true, match orders whenever an order is posted,
        #   otherwise do so at the end of each period
        self.continuous_order_matching: bool = continuous_order_matching

        # Money Supply
        self.havven_supply = Dec(havven_settings['havven_supply'])
        self.nomin_supply = Dec(havven_settings['nomin_supply'])
        self.escrowed_havvens = Dec(0)

        # Havven's own capital supplies
        self.havvens: Dec = self.havven_supply
        self.nomins: Dec = self.nomin_supply
        self.fiat = Dec(0)

        self.rolling_avg_time_window: int = havven_settings['rolling_avg_time_window']
        self.volume_weighted_average: bool = havven_settings['use_volume_weighted_avg']
        """Whether to calculate the rolling average taking into account the volume of the trades"""

    @classmethod
    def round_float(cls, value: float) -> Dec:
        """
        Round a float (as a Decimal) to the number of decimal places specified by
        the precision setting.
        Equivalent to Dec(value).quantize(Dec(1e(-cls.currency_precision))).
        """
        # This check for numbers which are smaller than the precision allows will
        # be commented out for now as it seems to kill economic activity.
        # if value < 1E-8:
        #     return Dec(0)
        return round(Dec(value), cls.currency_precision)

    @classmethod
    def round_decimal(cls, value: Dec) -> Dec:
        """
        Round a Decimal to the number of decimal places specified by
        the precision setting.
        Equivalent to Dec(value).quantize(Dec(1e(-cls.currency_precision))).
        This function really only need be used for products and quotients.
        """
        # This check for numbers which are smaller than the precision allows will
        # be commented out for now as it seems to kill economic activity.
        # if value < Dec('1E-8'):
        #     return Dec(0)
        return round(value, cls.currency_precision)
