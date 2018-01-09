from agents import MarketPlayer
from decimal import Decimal as Dec
from typing import List, Any, Dict
from core import orderbook as ob
from managers.havvenmanager import HavvenManager as hm


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

    TODO: this currently works on the assumption the price target is 1, change it to use buffer
      and variable price target
    """

    issuance_orders: List[Dict[str, Any]] = []
    '''
    A list of nomins given to this player, how much remaining to sell,
    how much the player is owed and who deserves them
    '''

    burn_orders: List[Dict[str, Any]] = []
    '''
    A list of fiat given to this player, how many nomins to buy (to burn), and how
    much the player is owed, and what player deserves them
    '''

    total_redeemed: Dec = Dec()

    def step(self):
        # create trades in the order they arrive
        for item in self.issuance_orders:
            if item['trade'] is None:
                item['trade'] = self.place_nomin_fiat_ask_with_fee(
                    item['remaining'], 1-self.model.mint.non_discretionary_cap_buffer
                )
                if item['trade'] is None:
                    print(item)
                    print("remaining = 0:", item['remaining'] == 0)
                    print(self.portfolio())
                    raise Exception("trade is None...")

        for item in self.burn_orders:
            if item['trade'] is None:
                item['trade'] = self.place_nomin_fiat_bid_with_fee(
                    item['remaining'], 1+self.model.mint.non_discretionary_cap_buffer
                )
                if item['trade'] is None:
                    print(item)
                    print("remaining = 0:", item['remaining'] == 0)
                    print(self.portfolio())
                    raise Exception("trade is None...")

        self.issuance_orders = [i for i in self.issuance_orders if i['remaining'] > 0 or i['trade'] is None]
        self.burn_orders = [i for i in self.burn_orders if i['remaining'] > 0 or i['trade'] is None]

    def place_issuance_order(self, value: Dec, player: 'MarketPlayer') -> None:
        """
        Place an order to sell issued nomins for fiat, and send the fiat to the player
        """
        self.issuance_orders.append({
            'initial': value,
            'remaining': value,
            'player': player,
            'trade': None
        })

    def place_burn_order(self, value: Dec, player: 'MarketPlayer'):
        self.burn_orders.append({
            'initial': value,
            'remaining': value,
            'player': player,
            'trade': None
        })

    def notify_cancelled(self, order: "ob.LimitOrder") -> None:
        pass

    def notify_trade(self, record: "ob.TradeRecord") -> None:
        """
        Notify this agent that its order was filled.
        """
        if record.seller == self:
            # selling nomins, so issuing them into the market
            ask = record.ask
            order = None
            for order in self.issuance_orders:
                if order['remaining'] > 0:
                    break
            if order is None:
                raise Exception("No issue order with remaining > 0, even though ask trade got filled")
            if order['remaining'] < record.quantity:
                print("\n".join([str(i['trade']) for i in self.issuance_orders]))
                print(record)
                print(order)
                print(order['trade'])
                print(ask)
                raise Exception("issuance orders got filled in wrong order for some reason " +
                                f"({order['remaining']} < {record.quantity})")

            if ask.active:
                # order partially filled
                order['remaining'] -= record.quantity
                if order['remaining'] <= 0:
                    raise Exception("order remaining <= 0 when order partially filled")
                order['player'].fiat += record.price*record.quantity
                self.fiat -= record.price*record.quantity
            else:
                # order was filled completely
                order['player'].fiat += record.price*order['remaining']
                self.fiat -= record.price*record.quantity
                order['remaining'] = 0

        if record.buyer == self:
            # buying nomins, to burn them
            bid = record.bid
            order = None
            for order in self.burn_orders:
                if order['remaining'] > 0:
                    break
            if order is None:
                raise Exception("No burn order with remaining > 0, even though bid trade got filled")
            if order['remaining'] < record.quantity:
                raise Exception("burn orders got filled in wrong order for some reason " +
                                f"({order['remaining']} < {record.quantity})")
            if bid.active:
                # bid partially filled
                order['remaining'] -= record.quantity
                if order['remaining'] <= 0:
                    raise Exception("order remaining <= 0 when order partially filled")
                # refund excess fiat, if price was below 1 (should never be above)
                order['player'].fiat += record.quantity*(1-record.price)
                self.fiat -= record.quantity*(1-record.price)
            else:
                # order filled completely
                order['player'].fiat += record.quantity*(1-record.price)
                self.fiat -= record.quantity*(1-record.price)
                order['remaining'] = 0
        self.trades.append(record)






