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
    assert (bob.nomins == 0)
    assert (alice.nomins == alice_initial)
    assert (len(havven.schedule.agents) == 2)
    assert (len(havven.agent_manager.agents['others']) == 2)
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
        assert (alice.nomins == Dec(initial))
        assert (bob.nomins == 0)
        assert (havven.manager.nomins == 0)

    # return objects for additional checks if needed
    return alice, bob, havven


nomin_transfer_scenarios = [
    # scenarios are in the form: [initial_nomin_holdings, transfer_amount, should_it_succeed]

    # - Alice has more than enough nomins to fill the transfer with fee (i.e. 200 nomins):
    # -- Alice's resulting nomins = initial - 100*(1+fee_rate)
    # -- Bob's resulting nomins = 100
    # -- Havven accrues 100*fee_rate nomins in fees
    (200, 100, True),

    # - Alice has exactly enough nomins to fill the transfer with fee (i.e. 100*(1+fee_rate) nomins):
    # -- Alice’s resulting nomins = 0
    # -- Bob’s resulting nomins = 100
    # -- Havven accrues 100*fee_rate nomins in fees
    (Dec('100.5'), 100, True),

    # - Alice has exactly 100 nomins:
    # TODO: (?) -- Alice is notified transfer failed
    # -- Alice’s resulting nomins = 100
    # -- Bob’s resulting nomins = 0
    # -- Havven accrues no fees, as no transfer took place
    (100, 100, False),

    # - Alice has 0 nomins:
    # -- Same result as 100 nomins
    (0, 100, False),

    # - Alice has 100*(1+fee_rate) - (1E^(-currency_precision)) nomins (i.e. 100.49999...)
    # -- Same result as 100 nomins.
    (Dec("100.5") - Dec("1E-" + str(hm.currency_precision)), 100, False),

    # - Alice has 100*(1+fee_rate) - (5E^(-(1+currency_precision))) nomins
    # -- Aka. How is rounding handled.
    # -- Assuming the same result as: initial = 100*(1+fee_rate)
    (Dec("100.5") - Dec("5E-" + str(hm.currency_precision + 1)), 100, True),

    # - Alice has 100*(1+fee_rate) - (5E^(-(1+currency_precision))) nomins
    # -- Aka. How is rounding handled.
    # -- Assuming the same result as: initial = 100*(1+fee_rate)
    (Dec("100.5") - Dec("4.9E-" + str(hm.currency_precision + 1)), 100, True)
]


@pytest.mark.parametrize('initial, transfer_amount, success', [
    pytest.param(*i, id=f"{str(i[0])};{i[1]};{['fail','pass'][i[2]]}") for i in nomin_transfer_scenarios
])
def test_nomin_transfer_scenarios(initial, transfer_amount, success):
    transfer_nomins_checks(initial, transfer_amount, success)


"""
===========================================
= Testing limit sells 
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


def place_nomin_fiat_bid(havven, player, order_quant, order_price, success):
    """
    Place an nomin fiat limit sell (Ask) and check it's correctness
    matching on order should be disabled.
    """
    bid = player.place_nomin_fiat_bid(order_quant, order_price)
    if success:
        assert bid is not None
        assert bid.quantity == order_quant
        assert bid.fee == havven.fee_manager.transferred_fiat_fee(order_quant*order_price)
    else:
        assert bid is None
    return bid


placing_nomin_for_fiat_ask_scenarios = [
    # scenarios are in the form:
    #
    # [(alice_nomins, alice_ask_quant, alice_ask_price, success), ...]
    #
    # where the amount of bobs and charlies are variable, and they all place bids
    # where type is 0 for no match, 1 for completely filled, 2 for partially filled, 3 for failed place
    # Bob/Charlie/others should never fail to place, only Alice (i.e only have type 0, 1, 2)

    # - Alice has less than 100*(1+fee_rate) nomins
    # -- Trade doesn't get placed in all scenarios
    (0, 100, Dec('1.1'), False),
    (100, 100, Dec('1.1'), False),
    (Dec('100.5') - Dec("1E-" + str(hm.currency_precision)), 100, Dec('1.1'), False),

    # Test if an ask is placed when the user's initial value would be rounded below the
    # required amount to place the ask
    (Dec('100.5') - Dec("5.1E-" + str(hm.currency_precision+1)), 100, Dec('1.1'), False),

    # Alice has enough to place the order, but no limit buys exist
    (200, 100, Dec('1.1'), True),

    # Alice has barely enough to place the order, but no limit buys exist
    (Dec("100.5"), 100, Dec('1.1'), True),

    # Testing rounding, which should succeed
    (Dec("100.5") - Dec("5E-" + str(hm.currency_precision + 1)), 100, Dec('1.1'), True),
]


@pytest.mark.parametrize('initial, quantity, price, success', [
    pytest.param(
        *i,
        id=f"{str(i[0])};{i[1]}@{i[2]};{['fail','pass'][i[3]]}"
    ) for i in placing_nomin_for_fiat_ask_scenarios
])
def test_nomin_fiat_ask_scenarios(initial, quantity, price, success):
    nomin_ask_placement_check(initial, quantity, price, success)


def nomin_ask_placement_check(initial, quantity, price, success):
    havven = make_model_without_agents(match_on_order=False)
    alice = add_market_player(havven)
    alice.nomins = Dec(initial)

    ask = place_nomin_fiat_ask(havven, alice, quantity, price, success)
    if success:
        assert ask is not None
        assert alice.orders[0] == ask
        # test to check matching to nothing raises an exception
        with pytest.raises(Exception):
            ask.book.do_single_match()
        assert alice.available_nomins == havven.manager.round_decimal(initial - (ask.quantity + ask.fee))
        assert alice.available_nomins == initial - quantity - havven.fee_manager.transferred_nomins_fee(quantity)
        assert alice.nomins == initial
        ask.cancel()
        assert alice.available_nomins == havven.manager.round_decimal(initial)
        assert alice.nomins == havven.manager.round_decimal(initial)
    else:
        assert ask is None
        assert alice.nomins == havven.manager.round_decimal(initial)
        assert alice.fiat == 0


"""
===========================================
= Testing limit buys
===========================================
"""


def test_limit_buys():
    pass


"""
===========================================
= Testing testing limit sells matching existing buys
===========================================
"""

matching_nomin_for_fiat_ask_scenarios = [
    # scenarios are in the form:
    # [
    #   (alice_nomins, alice_ask_quant, alice_ask_price, type),
    #   (bob_fiat, bob_bid_quant, bob_bid_price, type),
    # ]
    #
    # where the amount of bobs is variable, and they all place bids
    # where type is 0 for no match, 1 for completely filled, 2 for partially filled
    # Placing orders should never fail as that isn't the point of this test
]

def test_exact_match():
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
    """
    alice_initial = Dec("200")
    havven, alice, bob, charlie = place_nom_fiat_limit_sell_setup(alice_initial)
    bob_bid = place_nomin_fiat_bid(havven, bob, Dec(100), Dec('1.1'), True)

    bob_initial = bob.fiat

    assert bob_bid is not None
    assert bob.orders[0] == bob_bid
    with pytest.raises(Exception):
        bob_bid.book.do_single_match()

    alice_ask = place_nomin_fiat_ask(havven, alice, Dec(100), Dec('1.1'), True)
    assert alice_ask is not None
    assert alice.orders[0] == alice_ask

    trade = alice_ask.book.do_single_match()

    assert trade is not None

    assert bob.nomins == Dec(100)
    assert bob.nomins == trade.quantity
    assert alice.nomins == alice_initial - Dec(100) - havven.fee_manager.transferred_nomins_fee(Dec(100))
    assert alice.nomins == alice_initial - trade.quantity - trade.ask_fee
    assert havven.manager.nomins == havven.fee_manager.transferred_nomins_fee(Dec(100))
    assert havven.manager.nomins == Dec(100) * havven.fee_manager.nom_fee_rate

    assert alice.fiat == trade.quantity * trade.price
    assert bob.fiat == (bob_initial - trade.quantity * trade.price - trade.bid_fee)
    assert bob.fiat == bob_initial - (Dec(100) * Dec('1.1') * (1 + havven.fee_manager.fiat_fee_rate))

    assert bob_bid.active is False
    assert alice_ask.active is False


def test_better_price_match():
    """
    -- Bob has a limit buy for 100 nomins @ 1.2
    --- Bob’s order already existed, so use the price 1.2
    --- Same result as above (except using 1.2 as the price)
    """
    alice_initial = Dec("200")
    havven, alice, bob, charlie = place_nom_fiat_limit_sell_setup(alice_initial)
    bob_bid = place_nomin_fiat_bid(havven, bob, Dec(100), Dec('1.2'), True)

    bob_initial = bob.fiat

    assert bob_bid is not None
    assert bob.orders[0] == bob_bid
    with pytest.raises(Exception):
        bob_bid.book.do_single_match()

    alice_ask = place_nomin_fiat_ask(havven, alice, Dec(100), Dec('1.1'), True)
    assert alice_ask is not None
    assert alice.orders[0] == alice_ask

    trade = alice_ask.book.do_single_match()

    assert trade is not None

    assert bob.nomins == Dec(100)
    assert bob.nomins == trade.quantity
    assert alice.nomins == alice_initial - Dec(100) - havven.fee_manager.transferred_nomins_fee(Dec(100))
    assert alice.nomins == alice_initial - trade.quantity - trade.ask_fee
    assert havven.manager.nomins == havven.fee_manager.transferred_nomins_fee(Dec(100))
    assert havven.manager.nomins == Dec(100) * havven.fee_manager.nom_fee_rate

    assert alice.fiat == trade.quantity * trade.price
    assert bob.fiat == (bob_initial - trade.quantity * trade.price - trade.bid_fee)
    assert bob.fiat == bob_initial - (Dec(100) * Dec('1.2') * (1 + havven.fee_manager.fiat_fee_rate))

    assert bob_bid.active is False
    assert alice_ask.active is False


def test_price_too_low_match():
    """
    -- Bob has a limit buy for 100 nomins @ 1.0
    --- The price is too low to match Alice’s order
    --- Alice’s order is placed, and added to the orderbook
    """
    alice_initial = Dec("200")
    havven, alice, bob, charlie = place_nom_fiat_limit_sell_setup(alice_initial)
    bob_bid = place_nomin_fiat_bid(havven, bob, Dec(100), Dec('1'), True)

    bob_initial = bob.fiat

    assert bob_bid is not None
    assert bob.orders[0] == bob_bid
    with pytest.raises(Exception):
        bob_bid.book.do_single_match()

    alice_ask = place_nomin_fiat_ask(havven, alice, Dec(100), Dec('1.1'), True)
    assert alice_ask is not None
    assert alice.orders[0] == alice_ask

    trade = alice_ask.book.do_single_match()

    assert trade is None

    assert alice.available_nomins == havven.manager.round_decimal(alice_initial - (alice_ask.quantity + alice_ask.fee))
    assert alice.nomins == alice_initial
    assert alice.fiat == Dec(0)

    assert bob.available_fiat == havven.manager.round_decimal(bob_initial - (bob_bid.quantity + bob_bid.fee))
    assert bob.fiat == bob_initial
    assert bob.nomins == Dec(0)

    alice_ask.cancel()
    bob_bid.cancel()

    assert alice.available_nomins == havven.manager.round_decimal(alice_initial)
    assert alice.nomins == alice_initial

    assert bob.available_fiat == bob_initial
    assert bob.fiat == bob_initial

    assert bob_bid.active is False
    assert alice_ask.active is False


def test_higher_quantity_buy():
    """
    -- Bob has a limit buy for 200 nomins @ 1.1
    --- Alice transfers 100 nomins to Bob
    --- Bob transfers 100*1.1 fiat to Alice
    --- Alice’s order is cancelled
    --- Bob’s order is updated
    ---- Quantity is reduced by 100
    ---- Bob’s order’s fee is recalculated
    ----- Fee started at 100*1.1*fee_rate
    ----- Fee is reduced by 50*1.1*fee_rate
    """
    alice_initial = Dec("200")
    havven, alice, bob, charlie = place_nom_fiat_limit_sell_setup(alice_initial)
    bob_bid = place_nomin_fiat_bid(havven, bob, Dec(200), Dec('1.1'), True)

    bob_initial = bob.fiat

    assert bob_bid is not None
    assert bob.orders[0] == bob_bid
    with pytest.raises(Exception):
        bob_bid.book.do_single_match()

    alice_ask = place_nomin_fiat_ask(havven, alice, Dec(100), Dec('1.1'), True)
    assert alice_ask is not None
    assert alice.orders[0] == alice_ask

    trade = alice_ask.book.do_single_match()

    assert bob.nomins == Dec(100)
    assert bob.nomins == trade.quantity

    assert alice.nomins == alice_initial - Dec(100) - havven.fee_manager.transferred_nomins_fee(Dec(100))
    assert alice.nomins == alice_initial - trade.quantity - trade.ask_fee

    assert alice.fiat == trade.quantity * trade.price
    assert bob.fiat == bob_initial - trade.quantity*trade.price - trade.bid_fee

    assert havven.manager.nomins == havven.fee_manager.transferred_nomins_fee(Dec(100))
    assert havven.manager.nomins == Dec(100) * havven.fee_manager.nom_fee_rate
    assert havven.manager.nomins == trade.ask_fee

    assert havven.manager.fiat == havven.fee_manager.transferred_fiat_fee(trade.quantity * trade.price)
    assert havven.manager.fiat == trade.bid_fee
    assert havven.manager.fiat == Dec(100) * Dec('1.1') * havven.fee_manager.fiat_fee_rate

    assert alice_ask.active is False

    assert bob_bid.quantity == Dec(100)
    assert bob_bid.fee == havven.fee_manager.transferred_fiat_fee(bob_bid.quantity * bob_bid.price)

    bob_bid.cancel()

    assert bob_bid.active is False


def test_higher_quantity_higher_price_buy():
    """same as above, except bid starts as 200@1.2"""
    alice_initial = Dec("200")
    havven, alice, bob, charlie = place_nom_fiat_limit_sell_setup(alice_initial)
    bob_bid = place_nomin_fiat_bid(havven, bob, Dec(200), Dec('1.2'), True)

    bob_initial = bob.fiat

    assert bob_bid is not None
    assert bob.orders[0] == bob_bid
    with pytest.raises(Exception):
        bob_bid.book.do_single_match()
    assert bob.unavailable_fiat == bob_bid.quantity * bob_bid.price + bob_bid.fee

    alice_ask = place_nomin_fiat_ask(havven, alice, Dec(100), Dec('1.1'), True)
    assert alice_ask is not None
    assert alice.orders[0] == alice_ask

    trade = alice_ask.book.do_single_match()

    assert bob.nomins == Dec(100)
    assert bob.nomins == trade.quantity

    assert alice.nomins == alice_initial - Dec(100) - havven.fee_manager.transferred_nomins_fee(Dec(100))
    assert alice.nomins == alice_initial - trade.quantity - trade.ask_fee

    assert alice.fiat == trade.quantity * trade.price
    assert bob.fiat == bob_initial - trade.quantity*trade.price - trade.bid_fee

    assert havven.manager.nomins == havven.fee_manager.transferred_nomins_fee(Dec(100))
    assert havven.manager.nomins == Dec(100) * havven.fee_manager.nom_fee_rate
    assert havven.manager.nomins == trade.ask_fee

    assert havven.manager.fiat == havven.fee_manager.transferred_fiat_fee(trade.quantity * trade.price)
    assert havven.manager.fiat == trade.bid_fee
    assert havven.manager.fiat == Dec(100) * Dec('1.2') * havven.fee_manager.fiat_fee_rate

    assert alice_ask.active is False

    assert bob_bid.quantity == Dec(100)
    assert bob_bid.fee == havven.fee_manager.transferred_fiat_fee(bob_bid.quantity * bob_bid.price)

    assert bob.unavailable_fiat == bob_bid.quantity * bob_bid.price + bob_bid.fee

    bob_bid.cancel()

    assert bob_bid.active is False


"""
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

TODO: same as above, but both at 1.1, to show the ordering is correct


TODO: test more precises prices eg. ask:100@1.32451234
TODO: testing buy limits thoroughly
TODO: testing market buy/sells (and implement if needed)
  - they're the same as sell_with_fee, should there really be a difference to limit buy/sell?
TODO: testing user buying from themselves (should be allowed, as it only benefits the system)
    - but then, should people buying from themselves influence the price?
        it probably shouldn't, but they could always just have two accounts anyways.
        is there any way to detect this?
        to stop high volume price manipulation by one user?
TODO: testing continuous buying/selling

"""
