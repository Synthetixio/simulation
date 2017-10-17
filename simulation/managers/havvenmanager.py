from decimal import Decimal as Dec


class HavvenManager:
    """
    Class to hold Havven's model variables
    """

    def __init__(self, utilisation_ratio_max: Dec = Dec(1),
                 match_on_order: bool = True) -> None:
        self.currency_precision = 8

        # Utilisation Ratio maximum (between 0 and 1)
        self.utilisation_ratio_max: Dec = utilisation_ratio_max

        # If true, match orders whenever an order is posted,
        #   otherwise do so at the end of each period
        self.match_on_order: bool = match_on_order

        # Money Supply
        self.curit_supply: Dec = Dec('10.0e9')
        self.nomin_supply: Dec = Dec('0.0')
        self.escrowed_curits: Dec = Dec('0.0')

        # Havven's own capital supplies
        self.curits: Dec = self.curit_supply
        self.nomins: Dec = self.nomin_supply
        self.fiat: Dec = self.escrowed_curits
