import pytest
import model
import orderbook
from decimal import Decimal as Dec


def make_model():
    return model.Havven(0)

def add_market_player(model):
    # model.add
    pass

"""
Test scenarios
Note: Unless otherwise specified, Initial/resulting currencies are the actor’s “available currency”,
      as currencies tied up in orders can’t be transferred.
Transfer Fees

Scenario 1
Alice wants to transfer 100 nomins to Bob, to help him start up his IT company.

She accesses her wallet, gets Bob to send her his wallet information. She then transfers the funds to him.

Scenarios: (Bob starting with no nomins)

- Alice has more than enough nomins to fill the transfer with fee (i.e. 200 nomins):
-- Alice’s resulting nomins = initial - 100*(1+fee_rate)
-- Bob’s resulting nomins = 100
-- Havven accrues 100*fee_rate nomins in fees

- Alice has exactly enough nomins to fill the transfer with fee (i.e. 100*(1+fee_rate) nomins):
-- Alice’s resulting nomins = 0
-- Bob’s resulting nomins = 100
-- Havven accrues 100*fee_rate nomins in fees

- Alice has exactly 100 nomins:
-- Alice is notified transfer failed (?)
-- Alice’s resulting nomins = 100
-- Bob’s resulting nomins = 0
-- Havven accrues no fees, as no transfer took place

- Alice has 100*(1+fee_rate) - (1E^(-currency_precision)) nomins
-- Same result as 100 nomins.

- Alice has 100*(1+fee_rate) - (5E^(-(1+currency_precision))) nomins
-- Aka. How is rounding handled.
-- Assuming the same result as: initial = 100*(1+fee_rate)

- Alice has 0 nomins:
-- Same result as 100 nomins

Scenario 2
Alice wants to trade on the exchange, she wants to limit sell 100 nomins @ 1.1fiat/nom  on the NOM/FIAT market
In all scenarios, the trade history can be checked to see if something was added, with the correct values. As well as adding other price metrics etc. and checking them.

Scenarios:
Alice tries to place a limit sell for 100 nomins @ 1.1:
- Alice has less than 100*(1+fee_rate) nomins
-- Trade doesn’t get placed in all scenarios

- Alice has more than 100*(1+fee_rate) nomins and Bob/Charlie already have limit buys
-- Bob has a limit buy for 100 nomins @ 1.1
--- Alice transfers 100 nomins to Bob
---- Alice resulting nomins = initial - 100*(1+fee_rate)
---- Bob’s resulting nomins = 100
---- Havven accrues 100*fee_rate nomins in fees
--- Bob transfers 100*1.1 fiat to Alice
---- Bob’s resulting fiat = initial - (100*1.1)*(1+fee_rate)
---- Alice’s resulting fiat = 100*1.1
---- Havven accrues 100*1.1*fee_rate fiat in fees
--- Both orders are cancelled

-- Bob has a limit buy for 100 nomins @ 1.2
--- Bob’s order already existed, so use the price 1.2
--- Same result as above (except using 1.2 as the price)

-- Bob has a limit buy for 100 nomins @ 1.0
--- The price is too low to match Alice’s order
--- Alice’s order is placed, and added to the orderbook

-- Bob has a limit buy for 200 nomins @ 1.1
--- Alice transfers 100 nomins to Bob
--- Bob transfers 100*1.1 fiat to Alice
--- Alice’s order is cancelled
--- Bob’s order is updated
---- Quantity is reduced by 100
---- Bob’s order’s fee is recalculated
----- Fee started at 100*1.1*fee_rate
----- Fee is reduced by 50*1.1*fee_rate

-- Bob has a limit buy for 50 nomins @ 1.1 and Charlie has a limit buy for 50 nom @ 1.2
--- Charlie’s order is matched first, as it is the higher price
--- Alice transfers 50 nomins to Charlie
--- Alice receives 50*1.2 fiat from Charlie
--- Havven accrues fees for both transfers
--- Charlies order is cancelled
--- Alice’s order is updated
---- Quantity is reduced by 50
---- Alice’s order’s fee is recalculated
----- Fee was originally 100*fee_rate
----- Max fee is now 50*fee_rate
---- Alice’s total nomins is reduced by 50*(1+fee_rate)
--- Bob’s order is then matched
--- Alice transfers 50 nomins to Bob
--- Alice receives 50*1.1 fiat from Bob
--- Bob’s order is cancelled
--- Alice’s order is cancelled
"""