from agents import marketplayer
from decimal import Decimal as Dec
from typing import List, NamedTuple
from util import orderbook as ob
from collections import namedtuple


Redemption: NamedTuple = namedtuple('Redemption', ['inital', 'remaining', 'owed', 'player', 'trade'])


class HavvenNominDumper(marketplayer):
    """
    The Havven Nomin Dumper is a player who sells nomins on behalf of the
    Havven system, and then sends the fiat back to the system.

    Realistically, a player doesn't need to exist for this in the real system,
    but for the sake of the model it makes controlling the logic of selling the nomins
    much easier.

    Nomins will be given to this player as soon as some player escrows some havvens,
    then this player will sell them, and send them back to the Havven system to transfer
    to the respective player
    """

    received_nomins: List[Redemption] = []
    '''
    A list of nomins given to this player, how much remaining to sell,
    how much the player is owed and who deserves them
    '''

    total_redeemed: Dec = Dec()

    def step(self):
        for item in self.received_nomins:
            if item.trade is None:
                pass


    def notify_cancelled(self, order: "ob.LimitOrder") -> None:
        """
        Notify this agent that its order was cancelled.
        """
        print('c', order.quantity)
        pass

    def notify_trade(self, record: "ob.TradeRecord") -> None:
        """
        Notify this agent that its order was filled.
        """
        print(record.seller == self)
        self.trades.append(record)