from agents import MarketPlayer
from decimal import Decimal as Dec
from typing import List, Any, Dict
from core import orderbook as ob


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
      and variable price target (non_discretionary_cap_buffer)
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
                    item['remaining'], Dec(1)  # - self.model.mint.non_discretionary_cap_buffer
                )
                if item['trade'] is None:
                    print("Fatal error with issuance")
                    print(item)
                    print(self.portfolio())
                    raise Exception("trade is None in IssuanceController")
            if item['remaining'] < Dec('0.00000005'):
                item['trade'].cancel()
                item['remaining'] = 0

        for item in self.burn_orders:
            if item['trade'] is None:
                item['trade'] = self.place_nomin_fiat_bid_with_fee(
                    item['remaining'], Dec(1)  # + self.model.mint.non_discretionary_cap_buffer
                )
                if item['trade'] is None:
                    print("Fatal error with issuance")
                    print(item)
                    print(self.portfolio())
                    raise Exception("trade is None in IssuanceController")
            if item['remaining'] < Dec('0.00000005'):
                item['trade'].cancel()
                item['remaining'] = 0

        self.issuance_orders = [
            i for i in self.issuance_orders if i['remaining'] > 0
        ]
        self.burn_orders = [
            i for i in self.burn_orders if i['remaining'] > 0
        ]

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
        # will only get notified once when they are both the buyer and seller

        if record.seller == self and record.buyer == self:

            ask = record.ask
            bid = record.bid
            burn_order = None
            for burn_order in self.burn_orders:
                if burn_order['remaining'] > 0:
                    break
            if burn_order is None:
                raise Exception("No burn order when IssuanceController matched himself")
            issuance_order = None
            for issuance_order in self.issuance_orders:
                if issuance_order['remaining'] > 0:
                    break
            if burn_order is None:
                raise Exception("No issuance order when IssuanceController matched himself")

            if issuance_order['remaining'] < burn_order['remaining']:
                if issuance_order['remaining'] < record.quantity:
                    raise Exception("issuance order < burn order and < record.quantity")
            elif burn_order['remaining'] < record.quantity:
                raise Exception("burn order <= issuance_order and < record.quantity")

            if ask.active and bid.active:
                raise Exception("Matching orders in IssuanceController both only partially filled.")

            if ask.active:
                issuance_order['remaining'] -= record.quantity
                if issuance_order['remaining'] <= 0:
                    raise Exception("issuance order remaining <= 0 when order partially filled")
                issuance_order['player'].fiat += record.quantity * (record.price - 1)
                self.fiat -= record.quantity
                self.nomins -= record.quantity

                burn_order['remaining'] = 0
            elif bid.active:
                issuance_order['player'].fiat += issuance_order['remaining'] * (record.price - 1)
                self.fiat -= issuance_order['remaining']
                self.nomins -= record.quantity
                issuance_order['remaining'] = 0

                burn_order['remaining'] -= record.quantity
                # bid partially filled
                if burn_order['remaining'] <= 0:
                    raise Exception("burn order remaining <= 0 when order partially filled")
            else:
                # both were filled completely

                # give the issuer the 'remainder', should be 0 when matching @ pn = 1
                issuance_order['player'].fiat += issuance_order['remaining']
                self.fiat -= record.quantity * record.price
                self.nomins -= record.quantity

                issuance_order['remaining'] = 0
                burn_order['remaining'] = 0

        elif record.seller == self:

            # selling nomins, so issuing them into the market
            ask = record.ask
            order = None
            for order in self.issuance_orders:
                if order['remaining'] > 0:
                    break
            if order is None:
                raise Exception("No issue order with remaining > 0, even though ask trade got filled")

            if order['remaining'] < record.quantity:
                raise Exception("issuance orders got filled in wrong order for some reason " +
                                f"({order['remaining']} < {record.quantity})")

            order['remaining'] -= record.quantity
            if ask.active:
                # order partially filled
                if order['remaining'] <= 0:
                    raise Exception("order remaining <= 0 when order partially filled")
                order['player'].fiat += (record.price - 1) * record.quantity
                self.fiat -= record.price * record.quantity
            else:
                # order was filled completely
                order['player'].fiat += order['remaining'] * (record.price - 1)
                self.fiat -= order['remaining'] * record.price
                order['remaining'] = 0

        elif record.buyer == self:
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

            order['remaining'] -= record.quantity

            if bid.active:
                # bid partially filled
                if order['remaining'] <= 0:
                    raise Exception("order remaining <= 0 when order partially filled")
                # refund excess fiat, if price was below 1 (should never be above)
                order['player'].fiat += record.quantity * (1 - record.price)
                self.nomins -= record.quantity
            else:
                # order filled completely
                order['player'].fiat += record.quantity * (1 - record.price)
                self.nomins -= record.quantity
                order['remaining'] = 0

        self.trades.append(record)
