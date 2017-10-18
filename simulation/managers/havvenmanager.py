from decimal import getcontext, ROUND_HALF_UP
from decimal import Decimal as Dec


class HavvenManager:
    """
    Class to hold Havven's model variables
    """

    currency_precision = 8
    """
    Number of decimal places for currency precision.
    The decimal context precision should be significantly higher than this.
    """

    def __init__(self, utilisation_ratio_max: Dec = Dec(1),
                 match_on_order: bool = True) -> None:
        # Set the decimal rounding mode
        getcontext().rounding = ROUND_HALF_UP

        # Utilisation Ratio maximum (between 0 and 1)
        self.utilisation_ratio_max: Dec = utilisation_ratio_max

        # If true, match orders whenever an order is posted,
        #   otherwise do so at the end of each period
        self.match_on_order: bool = match_on_order

        # Money Supply
        self.curit_supply: Dec = Dec('1e10')
        self.nomin_supply: Dec = Dec(0)
        self.escrowed_curits: Dec = Dec(0)

        # Havven's own capital supplies
        self.curits: Dec = self.curit_supply
        self.nomins: Dec = self.nomin_supply
        self.fiat: Dec = self.escrowed_curits

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
