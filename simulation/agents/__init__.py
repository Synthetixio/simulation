from .marketplayer import MarketPlayer
from .arbitrageur import Arbitrageur
from .banker import Banker
from .randomizer import Randomizer
from .centralbank import CentralBank
from .nomin_shorter import NominShorter, CuritEscrowNominShorter
from .merchant import Merchant, Buyer

# player names for the UI sliders
# these have to match the class names
player_names = [
    # 'CentralBank',
    'Arbitrageur',
    'Banker',
    'Randomizer',
    'NominShorter',
    'CuritEscrowNominShorter',
    'Merchant',
    'Buyer'
]
