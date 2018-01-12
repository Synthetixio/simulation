from .marketplayer import MarketPlayer
from .arbitrageur import Arbitrageur
from .banker import Banker
from .randomizer import Randomizer
from .centralbank import CentralBank
from .speculator import HavvenSpeculator, NaiveSpeculator
from .nominshorter import NominShorter, HavvenEscrowNominShorter
from .merchant import Merchant, Buyer
from .marketmaker import MarketMaker
from .issuancecontroller import IssuanceController
from .havvenfoundation import HavvenFoundation
from .maxnominissuer import MaxNominIssuer

# player names for the UI sliders
player_names = {
    # 'CentralBank': CentralBank,
    'Arbitrageur': Arbitrageur,
    'Banker': Banker,
    'Randomizer': Randomizer,
    'NominShorter': NominShorter,
    # 'HavvenEscrowNominShorter': HavvenEscrowNominShorter,
    'HavvenSpeculator': HavvenSpeculator,
    'NaiveSpeculator': NaiveSpeculator,
    'Merchant': Merchant,
    'Buyer': Buyer,
    'MarketMaker': MarketMaker,
    # 'IssuanceController': IssuanceController,
    'MaxNominIssuer': MaxNominIssuer,
}

# exclude players when showing profit %
players_to_exclude = ["Merchant", "Buyer", "IssuanceController", "HavvenFoundation"]
