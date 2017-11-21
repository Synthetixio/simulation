import pytest
from decimal import Decimal as Dec

import model


def test_fiat_value():
    havven_model = model.HavvenModel(10)
    assert(isinstance(havven_model.fiat_value(), Dec))
    assert(havven_model.fiat_value() == Dec(0))
    assert(havven_model.fiat_value(Dec(1), Dec(1), Dec(1)) > Dec(0))
    assert(havven_model.fiat_value(curits=Dec(0),
                             nomins=Dec(0),
                             fiat=Dec(1)) == Dec(1))
    assert(havven_model.fiat_value(curits=Dec(1)) <
           havven_model.fiat_value(curits=Dec(2)))
    assert(havven_model.fiat_value(nomins=Dec(1)) <
           havven_model.fiat_value(nomins=Dec(2)))
    assert(havven_model.fiat_value(fiat=Dec(1)) <
           havven_model.fiat_value(fiat=Dec(2)))


def test_endowment():
    havven_model = model.HavvenModel(10)
    agent = havven_model.schedule.agents[0]
    agent_pre_cur = agent.curits
    havven_pre_cur = havven_model.manager.curits

    havven_model.endow_curits(agent, Dec(0))
    havven_model.endow_curits(agent, Dec(-10))
    assert(agent.curits == agent_pre_cur)
    assert(havven_model.manager.curits == havven_pre_cur)

    endowment = Dec(100)
    havven_model.endow_curits(agent, endowment)
    assert(agent.curits == agent_pre_cur + endowment)
    assert(havven_model.manager.curits == havven_pre_cur - endowment)


def test_step():
    havven_model = model.HavvenModel(20)
    assert(havven_model.manager.time == 1)
    havven_model.step()
    assert(havven_model.manager.time == 2)

    time_delta = 100
    for _ in range(time_delta):
        havven_model.step()
    assert(havven_model.manager.time == time_delta + 2)


def test_fee_distribution_period():
    havven_model = model.HavvenModel(20)
    assert(havven_model.fee_manager.fees_distributed == Dec(0))
    assert(havven_model.manager.nomins == Dec(0))

    for _ in range(havven_model.fee_manager.fee_period - 1):
        havven_model.step()

    prenomins = havven_model.manager.nomins
    predistrib = havven_model.fee_manager.fees_distributed
    assert(prenomins > Dec(0))
    assert(predistrib == Dec(0))

    havven_model.step()

    postnomins = havven_model.manager.nomins
    postdistrib = havven_model.fee_manager.fees_distributed
    assert(postnomins == Dec(0))
    assert(prenomins <= postdistrib)
    assert(havven_model.manager.nomins == Dec(0))

