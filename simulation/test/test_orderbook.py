import pytest
import model
import orderbook
from decimal import Decimal as Dec
import agents as ag
from managers.havvenmanager import HavvenManager as hm

UID = 0
"""UID is a global id for all agents being added in the tests"""


def make_model_without_agents(match_on_order=True):
    havven = model.Havven(0, match_on_order=match_on_order)
    for item in havven.schedule.agents:
        havven.schedule.remove(item)
    havven.agent_manager.agents = {"others": []}
    return havven


def add_market_player(model):
    global UID
    player = ag.MarketPlayer(UID, model)
    UID += 1
    model.agent_manager.add(player)
    return player


"""
===========================================
= Testing transfer fees
===========================================

Alice wants to transfer 100 nomins to Bob, to help him start up his IT company.

She accesses her wallet, gets Bob to send her his wallet information. She then transfers the funds to him.

Bob starts with no nomins

TODO: This probably belongs in feemanager?
TODO: change initial values that are dependant on fee (i.e. where 100.5 is hardcoded)
"""


def transfer_nomins_setup(alice_initial: Dec):
    havven = make_model_without_agents()
    alice = add_market_player(havven)
    alice.nomins = alice_initial
    bob = add_market_player(havven)
    assert(bob.nomins == 0)
    assert(alice.nomins == alice_initial)
    assert(len(havven.schedule.agents) == 2)
    assert(len(havven.agent_manager.agents['others']) == 2)
    return havven, alice, bob


def transfer_nomins_checks(initial, transfer_amt, success):
    """
    Alice starts with initial, tries to transfer transfer_amt
    success tells the system whether the transfer is expected to pass
    """
    havven, alice, bob = transfer_nomins_setup(Dec(initial))
    assert (alice.nomins == Dec(initial))
    alice.transfer_nomins_to(bob, Dec(transfer_amt))

    # if the transfer should happen
    if success:
        # check alice's nomins manually, and using the function
        assert (alice.nomins == Dec(initial - transfer_amt * (1 + havven.fee_manager.nom_fee_rate)))
        assert (alice.nomins == Dec(initial - transfer_amt - havven.fee_manager.transferred_nomins_fee(transfer_amt)))
        # check bob's received nomins
        assert (bob.nomins == Dec(transfer_amt))
        assert (bob.nomins == havven.fee_manager.transferred_nomins_received(
            transfer_amt * (1 + havven.fee_manager.nom_fee_rate)
        ))
        # check havven's fees
        assert (havven.manager.nomins == transfer_amt * havven.fee_manager.nom_fee_rate)

    # if the transfer should fail
    else:
        assert(alice.nomins == Dec(initial))
        assert(bob.nomins == 0)
        assert(havven.manager.nomins == 0)

    # return objects for additional checks if needed
    return alice, bob, havven


def test_transfer_nomins_pass():
    """
    - Alice has more than enough nomins to fill the transfer with fee (i.e. 200 nomins):
    -- Alice’s resulting nomins = initial - 100*(1+fee_rate)
    -- Bob’s resulting nomins = 100
    -- Havven accrues 100*fee_rate nomins in fees
    """
    transfer_nomins_checks(200, 100, True)


def test_transfer_nomins_exact_pass():
    """- Alice has exactly enough nomins to fill the transfer with fee (i.e. 100*(1+fee_rate) nomins):
    -- Alice’s resulting nomins = 0
    -- Bob’s resulting nomins = 100
    -- Havven accrues 100*fee_rate nomins in fees
    """
    alice, bob, havven = transfer_nomins_checks(Dec('100.5'), 100, True)
    assert(alice.nomins == 0)


def test_transfer_nomins_fail():
    """
    - Alice has exactly 100 nomins:
    TODO: (?) -- Alice is notified transfer failed
    -- Alice’s resulting nomins = 100
    -- Bob’s resulting nomins = 0
    -- Havven accrues no fees, as no transfer took place
    """
    transfer_nomins_checks(100, 100, False)


def test_transfer_nomins_barely_fail():
    """
    - Alice has 100*(1+fee_rate) - (1E^(-currency_precision)) nomins (i.e. 100.49999...)
    -- Same result as 100 nomins.
    """
    initial = Dec("100.5") - Dec("1E-"+str(hm.currency_precision))
    transfer_nomins_checks(initial, 100, False)


def test_rounding_success():
    """
    - Alice has 100*(1+fee_rate) - (5E^(-(1+currency_precision))) nomins
    -- Aka. How is rounding handled.
    -- Assuming the same result as: initial = 100*(1+fee_rate)
    """
    initial = Dec("100.5") - Dec("5E-"+str(hm.currency_precision+1))
    transfer_nomins_checks(initial, 100, True)


def test_rounding_fail():
    """
    - Alice has 100*(1+fee_rate) - (5E^(-(1+currency_precision))) nomins
    -- Aka. How is rounding handled.
    -- Assuming the same result as: initial = 100*(1+fee_rate)
    """
    initial = Dec("100.5") - Dec("4.9E-"+str(hm.currency_precision+1))
    transfer_nomins_checks(initial, 100, True)


def test_no_nomins():
    """
    - Alice has 0 nomins:
    -- Same result as 100 nomins
    """
    transfer_nomins_checks(0, 100, False)


"""
===========================================
= Testing limit sells (Assuming limit buys work as intended)
===========================================

Alice wants to trade on the exchange, she wants to limit sell 100 nomins @ 1.1fiat/nom  on the NOM/FIAT market
In all scenarios, the trade history can be checked to see if something was added, with the correct values.
As well as adding other price metrics etc. and checking them.

Scenarios:
Alice tries to place a limit sell for 100 nomins @ 1.1:
"""


def place_nom_fiat_limit_sell_setup(alice_initial):
    """
    Create three actors to do the trades,
    start the two who will have existing buys with 10000 fiat,
    as that isn't what is being tested.

    Have the model match_on_order be False, to test that the
    bids/asks are created correctly
    """
    havven = make_model_without_agents(match_on_order=False)
    alice = add_market_player(havven)
    alice.nomins = Dec(alice_initial)
    bob = add_market_player(havven)
    bob.fiat = Dec(10000)
    charlie = add_market_player(havven)
    charlie.fiat = Dec(10000)
    return havven, alice, bob, charlie


def place_nomin_fiat_ask(havven, player, order_quant, order_price, success):
    """
    Place an nomin fiat limit sell (Ask) and check it's correctness
    matching on order should be disabled.
    """
    ask = player.place_nomin_fiat_ask(order_quant, order_price)
    if success:
        assert ask is not None
        assert ask.quantity == order_quant
        assert ask.fee == havven.fee_manager.transferred_nomins_fee(order_quant)
    else:
        assert ask is None
    return ask


def test_placing_with_zero_fail():
    """
    - Alice has less than 100*(1+fee_rate) nomins
    -- Trade doesn't get placed in all scenarios
    """
    havven, alice, bob, charlie = place_nom_fiat_limit_sell_setup(Dec(0))
    ask = place_nomin_fiat_ask(havven, alice, Dec(100), Dec('1.1'), False)
    assert ask is None
    assert alice.nomins == 0
    assert alice.fiat == 0


def test_placing_fail():
    """
    - Alice has less than 100*(1+fee_rate) nomins
    -- Trade doesn't get placed in all scenarios
    """
    havven, alice, bob, charlie = place_nom_fiat_limit_sell_setup(Dec(100))
    ask = place_nomin_fiat_ask(havven, alice, Dec(100), Dec('1.1'), False)
    assert ask is None
    assert alice.nomins == 100
    assert alice.fiat == 0


def test_placing_barely_fail():
    """
    - Alice has less than 100*(1+fee_rate) nomins
    -- Trade doesn't get placed in all scenarios
    """
    initial = Dec('100.5') - Dec("1E-"+str(hm.currency_precision))
    havven, alice, bob, charlie = place_nom_fiat_limit_sell_setup(initial)
    ask = place_nomin_fiat_ask(havven, alice, Dec(100), Dec('1.1'), False)
    assert ask is None
    assert alice.nomins == initial
    assert alice.fiat == 0


def test_placing_no_match():
    """Alice has enough to place the order, but no limit buts exist"""
    initial = Dec("200")
    havven, alice, bob, charlie = place_nom_fiat_limit_sell_setup(initial)
    ask = place_nomin_fiat_ask(havven, alice, Dec(100), Dec('1.1'), True)
    assert ask is not None
    assert alice.orders[0] == ask
    # test to check matching to nothing raises an exception
    with pytest.raises(Exception):
        ask.book.do_single_match()
    assert alice.available_nomins == initial - (ask.quantity + ask.fee)
    assert alice.nomins == initial
    ask.cancel()
    assert alice.available_nomins == initial
    assert alice.nomins == initial


def test_barely_placing_no_match():
    """Alice has barely enough to place the order, but no limit buts exist"""
    initial = Dec("100.5")
    havven, alice, bob, charlie = place_nom_fiat_limit_sell_setup(initial)
    ask = place_nomin_fiat_ask(havven, alice, Dec(100), Dec('1.1'), True)
    assert ask is not None
    assert alice.orders[0] == ask
    # test to check matching to nothing raises an exception
    with pytest.raises(Exception):
        ask.book.do_single_match()
    assert alice.available_nomins == initial - (ask.quantity + ask.fee)
    assert alice.available_nomins == 0
    assert alice.nomins == initial
    ask.cancel()
    assert alice.available_nomins == initial
    assert alice.nomins == initial


def test_barely_placing_rounding_no_match():
    initial = Dec("100.5") - Dec("4.9E-"+str(hm.currency_precision+1))
    havven, alice, bob, charlie = place_nom_fiat_limit_sell_setup(initial)
    ask = place_nomin_fiat_ask(havven, alice, Dec(100), Dec('1.1'), True)
    assert ask is not None
    assert alice.orders[0] == ask
    # test to check matching to nothing raises an exception
    with pytest.raises(Exception):
        ask.book.do_single_match()
    assert alice.available_nomins == havven.manager.round_decimal(initial - (ask.quantity + ask.fee))
    assert alice.available_nomins == 0
    assert alice.nomins == initial
    ask.cancel()
    assert alice.available_nomins == havven.manager.round_decimal(initial)
    assert alice.nomins == initial

"""
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