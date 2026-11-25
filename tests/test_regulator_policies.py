from dataclasses import replace

import pytest

from config.settings import MarketSettings, RegulatorSettings, SimulationSettings
from src.experiments import POLICY_SCENARIOS, REGULATOR_OVERRIDES, SCENARIOS, run_experiments
from src.external_grid import GRID_ACCOUNT
from src.forecasting import generate_inputs
from src.households import generate_households
from src.ledger import Ledger
from src.market import Offer, Transaction
from src.metrics import calculate_metrics
from src.regulator import Regulator
from src.simulator import run_simulation


def grid(tid, meter, kwh, exporting):
    return Transaction(tid, 0, "grid", meter if exporting else GRID_ACCOUNT,
                       GRID_ACCOUNT if exporting else meter, kwh, .06 if exporting else .3)


def test_missed_local_fee_charges_only_the_energy_a_neighbour_could_have_traded():
    regulator = Regulator(RegulatorSettings(fee_scope="missed_local", grid_fee_eur_kwh=.01))
    regulator.begin_hour(0)
    ledger = Ledger()
    groups = {"S": 1, "B": 1, "N": 2}
    # Group 1: 2 kWh exported while 5 kWh imported -> 2 kWh missed on each side.
    # Group 2: night-like import with no neighbour exporting -> no fee.
    trades = [grid("g1", "S", 2, True), grid("g2", "B", 5, False), grid("g3", "N", 4, False)]
    regulator.end_hour(trades, ledger, groups)
    fees = {m.payer: m.amount_eur for m in ledger.movements if m.kind == "grid_fee"}
    assert fees["S"] == pytest.approx(2 * .01)
    assert fees["B"] == pytest.approx(2 * .01)  # 5 kWh imported, 2 kWh of it was avoidable
    assert "N" not in fees
    assert regulator.funds_eur == pytest.approx(.04)


def test_all_grid_fee_is_unchanged_by_default():
    regulator = Regulator(RegulatorSettings(grid_fee_eur_kwh=.01))
    regulator.begin_hour(0)
    ledger = Ledger()
    regulator.end_hour([grid("g1", "S", 2, True), grid("g2", "N", 4, False)], ledger)
    assert regulator.funds_eur == pytest.approx(.06)


def test_refund_returns_the_whole_fund_in_proportion_to_p2p_energy():
    regulator = Regulator(RegulatorSettings(initial_budget_eur=9.0, refund_leftover=True))
    regulator.begin_hour(0)
    ledger = Ledger()
    p2p = [Transaction("p1", 0, "p2p", "S", "B", 2.0, .2), Transaction("p2", 0, "p2p", "S", "C", 1.0, .2)]
    regulator.end_hour(p2p, ledger, day_end=True)
    refunds = {m.payee: m.amount_eur for m in ledger.movements if m.kind == "refund"}
    # S traded 3 kWh, B 2 kWh, C 1 kWh -> shares 3/6, 2/6, 1/6 of EUR 9.
    assert refunds == pytest.approx({"S": 4.5, "B": 3.0, "C": 1.5})
    assert regulator.funds_eur == pytest.approx(0, abs=1e-12)
    assert regulator.history[-1]["refund_eur"] == pytest.approx(9.0)


def test_refund_waits_for_the_end_of_the_day():
    regulator = Regulator(RegulatorSettings(initial_budget_eur=9.0, refund_leftover=True))
    regulator.begin_hour(0)
    ledger = Ledger()
    regulator.end_hour([Transaction("p1", 0, "p2p", "S", "B", 2.0, .2)], ledger, day_end=False)
    assert not [m for m in ledger.movements if m.kind == "refund"] and regulator.funds_eur == 9.0


def test_budget_sized_reward_spends_the_fund_on_possible_p2p_energy():
    settings = RegulatorSettings(initial_budget_eur=1.0, reward_mode="budget_sized", max_reward_eur_kwh=.10)
    offers = [Offer("S", 1, 30.0, .2, .1), Offer("B", 1, -20.0, .2, .1), Offer("X", 2, 5.0, .2, .1)]
    regulator = Regulator(settings)
    regulator.begin_hour(0, offers)
    # Group 1 can trade at most min(30, 20) = 20 kWh; group 2 has no buyer.
    assert regulator.reward_rate_eur_kwh == pytest.approx(1.0 / 20)
    capped = Regulator(replace(settings, initial_budget_eur=100.0))
    capped.begin_hour(0, offers)
    assert capped.reward_rate_eur_kwh == .10
    night = Regulator(settings)
    night.begin_hour(0, [Offer("B", 1, -3.0, .2, .1)])
    assert night.reward_rate_eur_kwh == 0


def test_policy_settings_are_validated():
    for bad in ({"fee_scope": "some"}, {"reward_mode": "other"}, {"refund_leftover": 1},
                {"max_reward_eur_kwh": -1}):
        with pytest.raises(ValueError):
            RegulatorSettings(**bad)


def test_every_policy_keeps_energy_and_money_balanced():
    settings = SimulationSettings()
    households = generate_households(settings)
    inputs = generate_inputs(households, settings)
    for name in POLICY_SCENARIOS:
        result = run_simulation(households, inputs, settings, MarketSettings(), name,
                                regulation_enabled=True, blockchain_enabled=False,
                                regulator_settings=replace(RegulatorSettings(), **REGULATOR_OVERRIDES[name]))
        metrics = calculate_metrics(result)  # raises if energy or money do not reconcile
        assert metrics["regulator_reward_expenditure_eur"] <= (
            metrics["regulator_fee_revenue_eur"] + metrics["regulator_initial_funds_eur"] + 1e-9)
        assert abs(metrics["financial_reconciliation_error_eur"]) < 1e-7
        if name == "J":
            assert metrics["regulator_remaining_funds_eur"] == pytest.approx(0, abs=1e-9)
            assert metrics["regulator_refund_eur"] > 0


def test_policy_scenarios_record_their_overrides(tmp_path):
    from main import load_configuration
    comparison = run_experiments(load_configuration(None), tmp_path, ["B", *POLICY_SCENARIOS], charts=False)
    by_name = {s["scenario"]: s for s in comparison["scenarios"]}
    assert all(SCENARIOS[name] == SCENARIOS["B"] for name in POLICY_SCENARIOS)
    assert by_name["G"]["configuration"]["regulator"]["grid_fee_eur_kwh"] == .0025
    assert by_name["H"]["configuration"]["regulator"]["upper_reward_eur_kwh"] == .075
    assert by_name["I"]["configuration"]["experiment"]["regulator_overrides"] == {"fee_scope": "missed_local"}
    # J changes only where the money goes after trading, so its energy matches B exactly.
    assert by_name["J"]["metrics"]["p2p_energy_kwh"] == by_name["B"]["metrics"]["p2p_energy_kwh"]
    assert by_name["J"]["metrics"]["household_net_cost_eur"] == pytest.approx(
        by_name["B"]["metrics"]["household_net_cost_eur"] - by_name["B"]["metrics"]["regulator_remaining_funds_eur"])


def test_an_unfunded_reward_keeps_the_guided_prices():
    regulator = Regulator(RegulatorSettings(initial_budget_eur=1.0, lower_tier_budget_eur=.5,
                                            upper_tier_budget_eur=.9, upper_reward_eur_kwh=.02))
    regulator.begin_hour(0)
    buyer = Offer("B", 1, -100.0, .20, .30, original_bid_eur_kwh=.12, original_ask_eur_kwh=.30)
    seller = Offer("S", 1, 100.0, .25, .18, original_bid_eur_kwh=.25, original_ask_eur_kwh=.28)
    # 100 kWh x EUR 0.02 = EUR 2 > EUR 1 in the fund: no reward, but guided bid/ask still apply.
    bid, ask, reward, reservation = regulator.quote(buyer, seller, 100.0)
    assert (bid, ask, reward, reservation) == (.20, .18, 0.0, None)
    assert bid >= ask  # the guided trade still clears, unlike the original .12 vs .28
