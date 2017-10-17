from decimal import Decimal


class HavvenManager:
    """
    Class to hold Havven's model variables
    """

    def __init__(self, utilisation_ratio_max: float = 1.0,
                 match_on_order: bool = True) -> None:
        self.currency_precision = 8

        # Utilisation Ratio maximum (between 0 and 1)
        self.utilisation_ratio_max: "Decimal" = Decimal.from_float(utilisation_ratio_max)

        # If true, match orders whenever an order is posted,
        #   otherwise do so at the end of each period
        self.match_on_order: bool = match_on_order

        # Money Supply
        self.curit_supply: "Decimal" = Decimal('10.0e9')
        self.nomin_supply: "Decimal" = Decimal('0.0')
        self.escrowed_curits: "Decimal" = Decimal('0.0')

        # Havven's own capital supplies
        self.curits: float = self.curit_supply
        self.nomins: float = self.nomin_supply
        self.fiat: float = self.escrowed_curits

