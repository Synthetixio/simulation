from agents import MarketPlayer
from decimal import Decimal as Dec
from typing import List, NamedTuple
from core import orderbook as ob
from collections import namedtuple


Redemption: NamedTuple = namedtuple('Redemption', ['initial', 'remaining', 'player', 'trade'])


class IssuanceController(MarketPlayer):
    """
    The Issuance Controller is a player who sells nomins on behalf of the
      Havven system, and then sends the fiat back to the system.

    Realistically, a player doesn't need to exist to do this in the real system,
      but for the sake of the model, it makes controlling the logic of selling nomins
      as well as debugging much easier.

    Nomins will be given to this player as soon as some player escrows some havvens,
      then this player will sell them, and send them back to the Havven system to transfer
      to the respective player
    """

    issuance_orders: List[Redemption] = []
    '''
    A list of nomins given to this player, how much remaining to sell,
    how much the player is owed and who deserves them
    '''

    burn_orders: List[Redemption] = []
    '''
    A list of fiat given to this player, how many nomins to buy (to burn), and how
    much the player is owed, and what player deserves them
    '''

    total_redeemed: Dec = Dec()

    def step(self):
        for item in self.issuance_orders:
            if item.trade is None:
                trade = self.place_nomin_fiat_ask_with_fee(
                    item.remaining, Dec(1-self.model.mint.non_discretionary_cap_buffer)
                )
                # if the trade was filled instantly, should be cleared in notify_trade logic
                item.trade = trade
            if item.trade.quantity + item.trade.fee < item.remaining:
                to_transfer = item.remaining - item.trade.quantity
                if self.available_fiat > to_transfer:
                    self.fiat -= to_transfer
                    item.player.fiat += to_transfer
                    item.remaining -= (to_transfer + item.trade.fee)

        for item in self.burn_orders:
            if item.trade is None:
                trade = self.place_nomin_fiat_bid_with_fee(
                    item.remaining, Dec(1+self.model.mint.non_discretionary_cap_buffer)
                )
                # if the trade was filled instantly, should be cleared in notify_trade logic
                item.trade = trade

            if item.trade.quantity + item.trade.fee < item.remaining:
                to_burn = item.remaining - item.trade.quantity
                if self.available_nomins > to_burn:
                    self.nomins -= to_burn
                    item.player.issued_nomins -= to_burn

        self.issuance_orders = [i for i in self.issuance_orders if i.remaining > 0]
        self.burn_orders = [i for i in self.burn_orders if i.remaining > 0]

    def place_issuance_order(self, value: Dec, player: 'MarketPlayer') -> None:
        self.issuance_orders.append(Redemption(value, value, player, None))

    def place_burn_order(self, value: Dec, player: 'MarketPlayer'):
        self.burn_orders.append(Redemption(value, value, player, None))

    def notify_cancelled(self, order: "ob.LimitOrder") -> None:
        raise Exception('Order was cancelled for issuance controller', order)
        pass

    def notify_trade(self, record: "ob.TradeRecord") -> None:
        """
        Notify this agent that its order was filled.
        """
        if record.seller == self:
            pass
        if record.buyer == self:
            pass
        self.trades.append(record)
