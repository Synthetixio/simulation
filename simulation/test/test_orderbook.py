import model
import orderbook
from decimal import Decimal

def make_book():
    return model.Havven(100).market_manager.nomin_fiat_market
