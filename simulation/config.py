"""
Static config values for Havven
"""


class FeeConfig:
    """
    Class to hold static fee values
    Note, updating values could be added fairly easily
    """
    # Fees
    fee_period: int = 50

    # Transfer fees in %
    nom_transfer_fee_rate: float = 0.005
    cur_transfer_fee_rate: float = 0.01
    fiat_transfer_fee_rate: float = 0.0

    # Issuance fee in %
    issuance_fee_rate: float = 0.0
    redemption_fee_rate: float = 0.0

