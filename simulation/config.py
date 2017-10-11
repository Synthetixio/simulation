

class HavvenSettings:
    """
    Class to hold Havven's model settings
    """

    # Utilisation Ratio maximum (between 0 and 1)
    utilisation_ratio_max: float = 1.0

    def __init__(self, num_agents: int, max_fiat: float = 1000, match_on_order: bool = True):
        # If true, match orders whenever an order is posted,
        #   otherwise do so at the end of each period
        self.match_on_order: bool = match_on_order
        self.max_fiat: float = max_fiat
        self.num_agents: int = num_agents

        # Market variables

        # Prices in fiat per token
        self.curit_price: float = 1.0
        self.nomin_price: float = 1.0

        # Money Supply
        self.curit_supply: float = 10.0**9
        self.nomin_supply: float = 0.0
        self.escrowed_curits: float = 0.0

        # Havven's own capital supplies
        self.curits: float = self.curit_supply
        self.nomins: float = 0.0
        self.fiat: float = 0.0


class FeeConfig:
    """
    Class to hold static fee values
    Note, updating values could be added fairly easily
    """
    # Fees
    fee_period: int = 50

    nom_transfer_fee_rate: float = 0.005
    cur_transfer_fee_rate: float = 0.01

    issuance_fee_rate: float = 0.01
    redemption_fee_rate: float = 0.02

    fiat_transfer_fee_rate: float = 0.0
