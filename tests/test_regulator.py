from random import Random

import pytest

from config.settings import MarketSettings, RegulatorSettings, SimulationSettings
from src.forecasting import generate_inputs
from src.households import generate_households
from src.ledger import Ledger
from src.market import Offer, Transaction
from src.p2p_market import trade_p2p
from src.regulator import Regulator
from src.simulator import run_simulation


@pytest.mark.parametrize("budget,rate", [(0, 0), (.999, 0), (1, .01), (4.999, .01), (5, .02)])
def test_tiers(budget, rate):
    regulator = Regulator(RegulatorSettings(initial_budget_eur=budget))
    regulator.begin_hour(0)
    assert regulator.reward_rate_eur_kwh == rate


def test_funded_discount_reward_and_ledger():
    regulator = Regulator(RegulatorSettings(initial_budget_eur=1))
    regulator.begin_hour(0)
    offers = [Offer("B", 1, -2, .196, .3), Offer("S", 1, 2, .1, .2)]
    trades = trade_p2p(offers, 0, Random(1), regulator)
    assert trades[0].price_eur_kwh == pytest.approx(.195)
    assert trades[0].reward_eur == pytest.approx(.02)
    assert regulator.funds_eur == pytest.approx(.98)
    assert regulator.reservations[0].status == "paid"
    ledger = Ledger()
    ledger.record_trade(trades[0])
    assert ledger.balance("S") == pytest.approx(2 * .195 + .02)
    assert ledger.balance("B") == pytest.approx(-2 * .195)


def test_unaffordable_reward_falls_back_to_original_compatible_offers():
    regulator = Regulator(RegulatorSettings(initial_budget_eur=1))
    regulator.begin_hour(0)
    offers = [Offer("B", 1, -200, .3, .3), Offer("S", 1, 200, .1, .2)]
    trades = trade_p2p(offers, 0, Random(1), regulator)
    assert trades[0].reward_eur == 0 and trades[0].price_eur_kwh == .2
    assert regulator.funds_eur == 1


def test_fees_cannot_finance_same_hour_and_rejected_quote_releases_funds():
    regulator = Regulator()
    regulator.begin_hour(0)
    assert regulator.reward_rate_eur_kwh == 0
    trades = trade_p2p([Offer("B", 1, -1, .2, .3), Offer("S", 1, 1, .1, .15)], 0, Random(1), regulator)
    assert len(trades) == 1 and trades[0].reward_eur == 0
    ledger = Ledger()
    regulator.end_hour([Transaction("g", 0, "grid", "external_grid", "B", 100, .3)], ledger)
    assert regulator.reward_rate_eur_kwh == 0
    assert regulator.funds_eur == 1
    regulator.begin_hour(1)
    assert regulator.reward_rate_eur_kwh == .01
    assert trade_p2p([Offer("B", 1, -1, .1, .3), Offer("S", 1, 1, .1, .3)], 1, Random(1), regulator) == []
    assert regulator.available_eur == 1
    assert regulator.reservations[-1].status == "released"


def test_regulated_day_financial_conservation_and_fee_base():
    settings = SimulationSettings()
    households = generate_households(settings)
    result = run_simulation(households, generate_inputs(households, settings), settings, regulation_enabled=True)
    regulator = result.regulator
    fees = sum(t.quantity_kwh * .01 for t in result.transactions if t.market == "grid")
    rewards = sum(t.reward_eur for t in result.transactions)
    assert sum(h["grid_fees_eur"] for h in regulator.history) == pytest.approx(fees)
    assert regulator.funds_eur == pytest.approx(fees - rewards)
    assert all(h["reward_paid_eur"] <= h["opening_funds_eur"] + 1e-10 for h in regulator.history)
    assert all(h["closing_funds_eur"] >= 0 for h in regulator.history)
    assert all(t.market == "p2p" for t in result.transactions if t.reward_eur)
    assert result.ledger.balance("regulator") == pytest.approx(regulator.funds_eur)


def test_competing_guarantees_cannot_overspend_and_hour_cannot_close_twice():
    regulator = Regulator(RegulatorSettings(initial_budget_eur=1))
    regulator.begin_hour(0)
    offers = [Offer("B", 1, -120, .3, .3), Offer("S1", 1, 60, .1, .2), Offer("S2", 1, 60, .1, .2)]
    trades = trade_p2p(offers, 0, Random(1), regulator)
    assert len(trades) == 2
    assert sum(t.reward_eur for t in trades) == pytest.approx(.6)
    assert regulator.funds_eur == pytest.approx(.4)
    assert sum(t.reward_eur == 0 for t in trades) == 1
    ledger = Ledger()
    regulator.end_hour([], ledger)
    with pytest.raises(ValueError, match="already closed"):
        regulator.end_hour([], ledger)
