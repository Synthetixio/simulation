import pytest
from decimal import Decimal as Dec

import model


def test_fiat_value():
    havven = model.HavvenModel(10)
    assert(isinstance(havven.fiat_value(), Dec))
    assert(havven.fiat_value() == Dec(0))
    assert(havven.fiat_value(Dec(1), Dec(1), Dec(1)) > Dec(0))
    assert(havven.fiat_value(curits=Dec(0),
                             nomins=Dec(0),
                             fiat=Dec(1)) == Dec(1))
    assert(havven.fiat_value(curits=Dec(1)) <
           havven.fiat_value(curits=Dec(2)))
    assert(havven.fiat_value(nomins=Dec(1)) <
           havven.fiat_value(nomins=Dec(2)))
    assert(havven.fiat_value(fiat=Dec(1)) <
           havven.fiat_value(fiat=Dec(2)))


def test_endowment():
    havven = model.HavvenModel(10)
    agent = havven.schedule.agents[0]
    agent_pre_cur = agent.curits
    havven_pre_cur = havven.manager.curits

    havven.endow_curits(agent, Dec(0))
    havven.endow_curits(agent, Dec(-10))
    assert(agent.curits == agent_pre_cur)
    assert(havven.manager.curits == havven_pre_cur)

    endowment = Dec(100)
    havven.endow_curits(agent, endowment)
    assert(agent.curits == agent_pre_cur + endowment)
    assert(havven.manager.curits == havven_pre_cur - endowment)


def test_step():
    havven = model.HavvenModel(20)
    assert(havven.manager.time == 1)
    havven.step()
    assert(havven.manager.time == 2)

    time_delta = 100
    for _ in range(time_delta):
        havven.step()
    assert(havven.manager.time == time_delta + 2)


def test_fee_distribution_period():
    havven = model.HavvenModel(20)
    assert(havven.fee_manager.fees_distributed == Dec(0))
    assert(havven.manager.nomins == Dec(0))

    for _ in range(havven.fee_manager.fee_period - 1):
        havven.step()

    prenomins = havven.manager.nomins
    predistrib = havven.fee_manager.fees_distributed
    assert(prenomins > Dec(0))
    assert(predistrib == Dec(0))

    havven.step()

    postnomins = havven.manager.nomins
    postdistrib = havven.fee_manager.fees_distributed
    assert(postnomins == Dec(0))
    assert(prenomins <= postdistrib)
    assert(havven.manager.nomins == Dec(0))

