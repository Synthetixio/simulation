"""model.py: The havven model itself lives here."""

from typing import Callable, Optional
import random

from scipy.stats import skewnorm

from mesa import Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector

import orderbook as ob
import modelstats as ms
import agents as ag


# Function signatures for transfers.
TransferTest = Callable[[ag.MarketPlayer, float], bool]
TransferFunction = Callable[[ag.MarketPlayer, ag.MarketPlayer, float], bool]


class Havven(Model):
    """
    An agent-based model of the Havven stablecoin system. This class will
      provide the basic market functionality of havven, an exchange, and a
      place for the market agents to live and interact.
    The aim is to stabilise the nomin price, but we would also like to measure
      other quantities including liquidity, volatility, wealth concentration,
      velocity of money and so on.
    """

    def __init__(self, N: int, max_fiat: float = 1000,
                 utilisation_ratio_max: float = 1.0,
                 match_on_order: bool = True) -> None:
        # Mesa setup
        super().__init__()
        self.schedule = RandomActivation(self)
        self.datacollector = DataCollector(
            model_reporters={
                "": lambda x: 0,  # Note: workaround for showing labels (more info server.py)
                "Nomin Price": lambda h: h.nom_fiat_market.price,
                "Curit Price": lambda h: h.cur_fiat_market.price,
                "Curit/Nomin Price": lambda h: h.cur_nom_market.price,
                "Havven Nomins": lambda h: h.nomins,
                "Havven Curits": lambda h: h.curits,
                "Havven Fiat": lambda h: h.fiat,
                "Gini": ms.gini,
                "Nomins": lambda h: h.nomin_supply,
                "Escrowed Curits": lambda h: h.escrowed_curits,
                "Wealth SD": ms.wealth_sd,
                "Max Wealth": ms.max_wealth,
                "Min Wealth": ms.min_wealth,
                "Profit %": ms.mean_profit_fraction,
                "Curit Demand": ms.curit_demand,
                "Curit Supply": ms.curit_supply,
                "Nomin Demand": ms.nomin_demand,
                "Nomin Supply": ms.nomin_supply,
                "Fiat Demand": ms.fiat_demand,
                "Fiat Supply": ms.fiat_supply,
                "Fee Pool": lambda h: h.nomins,
                "Fees Distributed": lambda h: h.fees_distributed,
                "NomCurOrderBook": lambda h: h.cur_nom_market,
                "FiatCurOrderBook": lambda h: h.cur_fiat_market,
                "FiatNomOrderBook": lambda h: h.nom_fiat_market
            }, agent_reporters={
                "Wealth": lambda agent: agent.wealth,
                "Name": lambda agent: agent.name
            })

        self.time: int = 1

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

        # Fees
        self.fee_period: int = 50
        self.fees_distributed: float = 0.0
        self.nom_transfer_fee_rate: float = 0.005
        self.cur_transfer_fee_rate: float = 0.01

        # TODO: charge issuance and redemption fees
        self.issuance_fee_rate: float = 0.01
        self.redemption_fee_rate: float = 0.02

        # TODO: Move fiat fees and currency pool into its own object
        self.fiat_transfer_fee_rate: float = 0.0

        # Utilisation Ratio maximum (between 0 and 1)
        self.utilisation_ratio_max: float = utilisation_ratio_max

        # If true, match orders whenever an order is posted,
        #   otherwise do so at the end of each period
        self.match_on_order: bool = match_on_order

        # Order books
        # If a book is X_Y_market, then X is the base currency,
        #   Y is the quote currency.
        # That is, buyers hold Y and sellers hold X.
        self.cur_nom_market: ob.OrderBook = ob.OrderBook(
            "CUR", "NOM", self.cur_nom_match, self.match_on_order
        )
        self.cur_fiat_market: ob.OrderBook = ob.OrderBook(
            "CUR", "FIAT", self.cur_fiat_match, self.match_on_order
        )
        self.nom_fiat_market: ob.OrderBook = ob.OrderBook(
            "NOM", "FIAT", self.nom_fiat_match, self.match_on_order
        )

        # Add the market participants
        self.num_agents: int = N

        fractions = {"banks": 0.25,
                     "arbs": 0.25,
                     "rands": 0.5}

        num_banks = int(N * fractions["banks"])
        num_rands = int(N * fractions["rands"])
        num_arbs = int(N * fractions["arbs"])

        i = 0

        for _ in range(num_banks):
            endowment = int(skewnorm.rvs(100)*max_fiat)
            self.schedule.add(ag.Banker(i, self, fiat=endowment))
            i += 1
        for _ in range(num_rands):
            self.schedule.add(ag.Randomizer(i, self, fiat=3*max_fiat))
            i += 1
        for _ in range(num_arbs):
            arbitrageur = ag.Arbitrageur(i, self, 0)
            self.endow_curits(arbitrageur, max_fiat)
            self.schedule.add(arbitrageur)
            i += 1

        reserve_bank = ag.MarketPlayer(i, self, 0)
        self.endow_curits(reserve_bank, 6 * N * max_fiat)
        self.schedule.add(reserve_bank)
        reserve_bank.sell_curits_for_fiat(N * max_fiat * 3)
        reserve_bank.sell_curits_for_nomins(N * max_fiat * 3)

    def fiat_value(self, curits: float, nomins: float, fiat: float) -> float:
        """Return the equivalent fiat value of the given currency basket."""
        return self.cur_to_fiat(curits) + self.nom_to_fiat(nomins) + fiat

    def endow_curits(self, agent: ag.MarketPlayer, curits: float) -> None:
        """Grant an agent an endowment of curits."""
        if curits > 0:
            value = min(self.curits, curits)
            agent.curits += value
            self.curits -= value

    def __bid_ask_match__(
            self, bid: ob.Bid, ask: ob.Ask,
            bid_success: TransferTest, ask_success: TransferTest,
            bid_transfer: TransferFunction,
            ask_transfer: TransferFunction) -> Optional[ob.TradeRecord]:
        """
        If possible, match the given bid and ask, with the given transfer
          and success functions.
        Cancel any orders which an agent cannot afford to service.
        Return a TradeRecord object if the match succeeded, otherwise None.
        """

        if ask.price > bid.price:
            return None

        # Price will be favourable to whoever went second.
        # The earlier poster trades at their posted price,
        #   while the later poster transacts at a price no worse than posted;
        #   they may do better.
        price = ask.price if ask.time < bid.time else bid.price
        quantity = min(ask.quantity, bid.quantity)
        buy_val = quantity*price

        # Only perform the actual transfer if it would be successful.
        # Cancel any orders that would not succeed.
        fail = False
        if not bid_success(bid.issuer, buy_val):
            bid.cancel()
            fail = True
        if not ask_success(ask.issuer, quantity):
            ask.cancel()
            fail = True
        if fail:
            return None

        # Perform the actual transfers.
        # We have already checked above if these would succeed.
        bid_transfer(bid.issuer, ask.issuer, buy_val)
        ask_transfer(ask.issuer, bid.issuer, quantity)

        # Update the orders, cancelling any with 0 remaining quantity.
        ask.update_quantity(ask.quantity - quantity)
        bid.update_quantity(bid.quantity - quantity)

        return ob.TradeRecord(bid.issuer, ask.issuer, price, quantity)

    def cur_nom_match(self, bid: ob.Bid,
                      ask: ob.Ask) -> Optional[ob.TradeRecord]:
        """
        Buyer offers nomins in exchange for curits from the seller.
        Return a TradeRecord object if the match succeeded, otherwise None.
        """
        return self.__bid_ask_match__(bid, ask,
                                      self.transfer_nomins_success,
                                      self.transfer_curits_success,
                                      self.transfer_nomins,
                                      self.transfer_curits)

    def cur_fiat_match(self, bid: ob.Bid,
                       ask: ob.Ask) -> Optional[ob.TradeRecord]:
        """
        Buyer offers fiat in exchange for curits from the seller.
        Return a TradeRecord object if the match succeeded, otherwise None.
        """
        return self.__bid_ask_match__(bid, ask,
                                      self.transfer_fiat_success,
                                      self.transfer_curits_success,
                                      self.transfer_fiat,
                                      self.transfer_curits)

    def nom_fiat_match(self, bid: ob.Bid,
                       ask: ob.Ask) -> Optional[ob.TradeRecord]:
        """
        Buyer offers fiat in exchange for nomins from the seller.
        Return a TradeRecord object if the match succeeded, otherwise None.
        """
        return self.__bid_ask_match__(bid, ask,
                                      self.transfer_fiat_success,
                                      self.transfer_nomins_success,
                                      self.transfer_fiat,
                                      self.transfer_nomins)

    def transfer_fiat_fee(self, value: float) -> float:
        """Return the fee charged for transferring a value of fiat."""
        return value * self.fiat_transfer_fee_rate

    def transfer_curits_fee(self, value: float) -> float:
        """Return the fee charged for transferring a value of curits."""
        return value * self.cur_transfer_fee_rate

    def transfer_nomins_fee(self, value: float) -> float:
        """Return the fee charged for transferring a value of nomins."""
        return value * self.nom_transfer_fee_rate

    def transfer_fiat_success(self, sender: ag.MarketPlayer,
                              value: float) -> bool:
        """True iff the sender could successfully send a value of fiat."""
        return 0 <= value + self.transfer_fiat_fee(value) <= sender.fiat

    def transfer_curits_success(self, sender: ag.MarketPlayer,
                                value: float) -> bool:
        """True iff the sender could successfully send a value of curits."""
        return 0 <= value + self.transfer_curits_fee(value) <= sender.curits

    def transfer_nomins_success(self, sender: ag.MarketPlayer,
                                value: float) -> bool:
        """True iff the sender could successfully send a value of nomins."""
        return 0 <= value + self.transfer_nomins_fee(value) <= sender.nomins

    def max_transferrable_fiat(self, principal: float) -> float:
        """
        A user can transfer less than their total balance when fees are
          taken into account.
          """
        return principal / (1 + self.fiat_transfer_fee_rate)

    def max_transferrable_curits(self, principal: float) -> float:
        """
        A user can transfer less than their total balance when fees are
          taken into account.
        """
        return principal / (1 + self.cur_transfer_fee_rate)

    def max_transferrable_nomins(self, principal: float) -> float:
        """
        A user can transfer less than their total balance when fees are
          taken into account.
        """
        return principal / (1 + self.nom_transfer_fee_rate)

    def transfer_fiat(self, sender: ag.MarketPlayer,
                      recipient: ag.MarketPlayer, value: float) -> bool:
        """
        Transfer a positive value of fiat currency from the sender to the
          recipient, if balance is sufficient. Return True on success.
        """
        if self.transfer_fiat_success(sender, value):
            fee = self.transfer_fiat_fee(value)
            sender.fiat -= value + fee
            recipient.fiat += value
            self.fiat += fee
            return True
        return False

    def transfer_curits(self, sender: ag.MarketPlayer,
                        recipient: ag.MarketPlayer, value: float) -> bool:
        """
        Transfer a positive value of curits from the sender to the recipient,
          if balance is sufficient. Return True on success.
        """
        if self.transfer_curits_success(sender, value):
            fee = self.transfer_curits_fee(value)
            sender.curits -= value + fee
            recipient.curits += value
            self.curits += fee
            return True
        return False

    def transfer_nomins(self, sender: ag.MarketPlayer,
                        recipient: ag.MarketPlayer, value: float) -> bool:
        """
        Transfer a positive value of nomins from the sender to the recipient,
          if balance is sufficient. Return True on success.
        """
        if self.transfer_nomins_success(sender, value):
            fee = self.transfer_nomins_fee(value)
            sender.nomins -= value + fee
            recipient.nomins += value
            self.nomins += fee
            return True
        return False

    def cur_to_nom(self, value: float) -> float:
        """Convert a quantity of curits to its equivalent value in nomins."""
        return (value * self.curit_price) / self.nomin_price

    def cur_to_fiat(self, value: float) -> float:
        """Convert a quantity of curits to its equivalent value in fiat."""
        return value * self.curit_price

    def nom_to_cur(self, value: float) -> float:
        """Convert a quantity of nomins to its equivalent value in curits."""
        return (value * self.nomin_price) / self.curit_price

    def nom_to_fiat(self, value: float) -> float:
        """Convert a quantity of nomins to its equivalent value in fiat."""
        return value * self.nomin_price

    def fiat_to_cur(self, value: float) -> float:
        """Convert a quantity of fiat to its equivalent value in curits."""
        return value / self.curit_price

    def fiat_to_nom(self, value: float) -> float:
        """Convert a quantity of fiat to its equivalent value in nomins."""
        return value / self.nomin_price

    def distribute_fees(self) -> None:
        """Distribute currently held nomins to holders of curits."""
        # Different fee modes:
        #  * distributed by held curits
        # TODO: * distribute by escrowed curits
        # TODO: * distribute by issued nomins
        # TODO: * distribute by motility

        pre_fees = self.nomins
        for agent in self.schedule.agents:
            if self.nomins == 0:
                break
            qty = min(agent.issued_nomins / self.nomins, self.nomins)
            agent.nomins += qty
            self.nomins -= qty
            self.fees_distributed += qty

    def step(self) -> None:
        """Advance the model by one step."""
        # Agents submit trades
        self.schedule.step()

        # Resolve outstanding trades
        if not self.match_on_order:
            self.cur_nom_market.match()
            self.cur_fiat_market.match()
            self.nom_fiat_market.match()

        # Distribute fees periodically.
        if (self.time % self.fee_period) == 0:
            self.distribute_fees()

        # Collect data
        self.datacollector.collect(self)

        self.time += 1
