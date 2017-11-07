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
    (Dec("100.5") - Dec("4.9E-" + str(hm.currency_precision + 1)), 100, True),
]


@pytest.mark.parametrize('initial, transfer_amount, success', [
    pytest.param(*i, id=f"{str(i[0])};{i[1]};{['fail','pass'][i[2]]}") for i in nomin_transfer_scenarios
])
def test_nomin_transfer_scenarios(initial, transfer_amount, success):
    transfer_nomins_checks(Dec(initial), Dec(transfer_amount), success)


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

    # test more precises prices and fees
    (200, 100, '1.11234113', True),

]


@pytest.mark.parametrize('initial, quantity, price, success', [
    pytest.param(
        *i,
        id=f"{str(i[0])};{i[1]}@{i[2]};{['fail','pass'][i[3]]}"
    ) for i in placing_nomin_for_fiat_ask_scenarios
])
def test_nomin_fiat_ask_scenarios(initial, quantity, price, success):
    nomin_ask_placement_check(Dec(initial), Dec(quantity), Dec(price), success)


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
    raise Exception("TODO")


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
    #   ...
    # ]
    #
    # where the amount of bobs is variable, and they all place bids
    # where type is 0 for no match, 1 for completely filled, 2 for partially filled
    # Placing orders should never fail as that isn't the point of these tests


    # - Alice has more than 100*(1+fee_rate) nomins and Bob/Charlie already have limit buys
    # -- Bob has a limit buy for 100 nomins @ 1.1
    # --- Alice transfers 100 nomins to Bob
    # ---- Alice resulting nomins = initial - 100*(1+fee_rate)
    # ---- Bob’s resulting nomins = 100
    # ---- Havven accrues 100*fee_rate nomins in fees
    # --- Bob transfers 100*1.1 fiat to Alice
    # ---- Bob’s resulting fiat = initial - (100*1.1)*(1+fee_rate)
    # ---- Alice’s resulting fiat = 100*1.1
    # ---- Havven accrues 100*1.1*fee_rate fiat in fees
    # --- Both orders are cancelled
    [
        (200, 100, '1.1', 1),
        (1000, 100, '1.1', 1)
    ],

    # -- Bob has a limit buy for 100 nomins @ 1.2
    # --- Bob’s order already existed, so use the price 1.2
    # --- Same result as above (except using 1.2 as the price)
    [
        (200, 100, '1.1', 1),
        (1000, 100, '1.2', 1)
    ],

    # -- Bob has a limit buy for 100 nomins @ 1.0
    # --- The price is too low to match Alice’s order
    # --- Alice’s order is placed, and added to the orderbook
    [
        (200, 100, '1.1', 0),
        (1000, 100, '1.0', 0)
    ],

    # -- Bob has a limit buy for 200 nomins @ 1.1
    # --- Alice transfers 100 nomins to Bob
    # --- Bob transfers 100*1.1 fiat to Alice
    # --- Alice’s order is cancelled
    # --- Bob’s order is updated
    # ---- Quantity is reduced by 100
    # ---- Bob’s order’s fee is recalculated
    # ----- Fee started at 100*1.1*fee_rate
    # ----- Fee is reduced by 50*1.1*fee_rate
    [
        (200, 100, '1.1', 1),
        (1000, 200, '1.1', 2)
    ],

    # Same as above, except using 1.2 as the bid price
    [
        (200, 100, '1.1', 1),
        (1000, 200, '1.2', 2)
    ],

    # -- Bob has a limit buy for 50 nomins @ 1.1 and Charlie has a limit buy for 50 nom @ 1.2
    # --- Charlie’s order is matched first, as it is the higher price
    # --- Alice transfers 50 nomins to Charlie
    # --- Alice receives 50*1.2 fiat from Charlie
    # --- Havven accrues fees for both transfers
    # --- Charlies order is cancelled
    # --- Alice’s order is updated
    # ---- Quantity is reduced by 50
    # ---- Alice’s order’s fee is recalculated
    # ----- Fee was originally 100*fee_rate
    # ----- Max fee is now 50*fee_rate
    # ---- Alice’s total nomins is reduced by 50*(1+fee_rate)
    # --- Bob’s order is then matched
    # --- Alice transfers 50 nomins to Bob
    # --- Alice receives 50*1.1 fiat from Bob
    # --- Bob’s order is cancelled
    # --- Alice’s order is cancelled

    [
        (200, 100, '1.1', 1),
        (1000, 50, '1.1', 1),
        (1000, 50, '1.2', 1)

    ],
    # same as above, but alice wants to sell more, so she is left with an order
    [
        (200, 150, '1.1', 2),
        (1000, 50, '1.1', 1),
        (1000, 50, '1.2', 1)

    ],

    # test more precise prices
    [
        (200, 100, '1.11234113', 1),
        (1000, 100, '1.23222117', 1)
    ]
]


@pytest.mark.parametrize('player_info', [
    pytest.param(
        i,
        id=f"{';'.join(['no_match','filled','partial'][x[3]] for x in i)}"
    ) for i in matching_nomin_for_fiat_ask_scenarios
])
def test_nomin_fiat_ask_match_scenarios(player_info):
    nomin_fiat_ask_match_check(player_info)


def nomin_fiat_ask_match_check(player_info):
    a_info = player_info.pop(0)

    a_initial = Dec(a_info[0])
    a_quant = Dec(a_info[1])
    a_price = Dec(a_info[2])
    a_type = a_info[3]

    havven = make_model_without_agents(match_on_order=False)
    alice = add_market_player(havven)
    alice.nomins = Dec(a_initial)

    others = []
    for item in player_info:
        data = {
            'initial': Dec(item[0]),
            'quant': Dec(item[1]),
            'price': Dec(item[2]),
            'type': item[3]
        }
        player = add_market_player(havven)
        player.fiat = data['initial']
        bid = place_nomin_fiat_bid(havven, player, data['quant'], data['price'], True)
        assert bid is not None
        assert player.orders[-1] == bid
        with pytest.raises(Exception):
            bid.book.do_single_match()
        data['bid'] = bid
        data['player'] = player
        others.append(data)

    others.sort(key=lambda x: (-x['price'], x['bid'].time))

    ask = place_nomin_fiat_ask(havven, alice, a_quant, a_price, True)
    assert ask is not None
    assert alice.orders[-1] == ask

    a_last_nom = a_initial
    a_last_fiat = Dec(0)
    last_havven_nomins = havven.manager.nomins
    last_havven_fiat = havven.manager.fiat

    while True:

        # if the order was cancelled/filled
        if not ask.active:
            assert a_type == 1

        if len(others) > 0:
            b = others.pop(0)
            bid = b['bid']
            b_initial = b['initial']
            b_quant = b['quant']
            b_price = b['price']
            b_type = b['type']
            bob = b['player']
        else:  # all bids were used
            # if the ask wasn't filled at all
            if ask.quantity == a_quant:
                assert a_type == 0
            # if the order wasn't filled completely
            elif ask.active:
                assert a_type == 2
            else:
                raise Exception("shouldn't be possible to be here...")
            break

        trade = ask.book.do_single_match()  # bid should always exist, when len(others) > 0
        if trade is None:
            # bid exists but prices don't match
            if ask.quantity == a_quant:
                # order wasn't filled at all
                assert a_type == 0
                assert b_type == 0
            else:
                # order is partially filled
                assert a_type == 2
                assert b_type == 0
            break

        # this should be enough to show the correct ordering of the sorted others?
        assert trade.buyer == bob
        assert trade.seller == alice

        if ask.active:
            if bid.active:
                raise Exception("trade matched but both bid and ask are active")
            else:
                # bid was completely filled, ask still exists
                assert b_type == 1
                # a_type assert doesn't happen here, as there will be more trades
                assert bob.nomins == trade.quantity
                assert alice.nomins == a_last_nom - trade.quantity - trade.ask_fee
                assert bob.fiat == b_initial - trade.quantity*trade.price - trade.bid_fee
                assert alice.fiat == a_last_fiat + trade.quantity * trade.price
                assert havven.manager.nomins == last_havven_nomins + trade.ask_fee
                assert havven.manager.fiat == last_havven_fiat + trade.bid_fee
                last_havven_nomins = havven.manager.nomins
                last_havven_fiat = havven.manager.fiat
                a_last_nom = alice.nomins
                a_last_fiat = alice.fiat
                continue

        else:
            if bid.active:
                # ask was completely filled, bid still exists
                assert a_type == 1
                assert b_type == 2
                # TODO: don't rely so heavily on trade variables
                assert bob.nomins == trade.quantity

                assert alice.nomins == a_last_nom - trade.quantity - trade.ask_fee
                assert bob.fiat == b_initial - trade.quantity*trade.price - trade.bid_fee
                assert alice.fiat == trade.quantity * trade.price
                assert havven.manager.nomins == last_havven_nomins + trade.ask_fee
                assert havven.manager.fiat == last_havven_fiat + trade.bid_fee
                break
            else:
                # both bid and ask were completely filled
                assert a_type == 1
                assert b_type == 1
                assert bob.nomins == trade.quantity
                assert bob.nomins == b_quant
                assert alice.nomins == a_last_nom - trade.quantity - trade.ask_fee
                assert bob.fiat == b_initial - trade.quantity*trade.price - trade.bid_fee
                assert bob.fiat == hm.round_decimal(
                    b_initial - (b_quant * hm.round_decimal(b_price) * (1 + havven.fee_manager.fiat_fee_rate))
                )
                assert alice.fiat == a_last_fiat + b_quant * b_price
                assert alice.fiat == a_last_fiat + trade.quantity * trade.price
                assert havven.manager.nomins == last_havven_nomins + trade.ask_fee
                assert havven.manager.fiat == last_havven_fiat + trade.bid_fee
                break

    if a_type == 1:
        assert not ask.active
    if a_type == 2:
        assert len(others) == 0
    if a_type == 0:
        if len(others) == 0:
            assert a_quant == ask.quantity
        else:
            assert others[0]['type'] == 0

    for item in others:
        if item['type'] == 1:
            assert item['bid'].active
            item['bid'].cancel()
            assert item['player'].fiat == item['initial']

        if item['type'] == 2:
            # could probably check more than that it is the first item
            assert item is others[0]['bid']


"""
TODO: test more precises prices eg. ask:100@1.32451234
TODO: testing buy limits thoroughly
TODO: testing market buy/sells (and implement if needed)
  - they're the same as sell_with_fee, should there really be a difference to limit buy/sell?
TODO: testing user buying from themselves (should be allowed, as it only benefits the system)
  - but then, should people buying from themselves influence the price?
        it probably shouldn't, and they could always just have two accounts anyways.
        is there any way to detect this?
        to stop high volume price manipulation by one user?
TODO: testing continuous buying/selling for decimal imprecision
  - one test could be quantity and price are both 1/7, for 100 bids, matched with an ask of
      70, at the same price etc.
"""
