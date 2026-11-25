"""Scenario L = F's battery order (P2P before charging, regulated) + K's fund-sized reward."""

from dataclasses import replace

import pytest

from main import load_configuration
from src.experiments import REGULATOR_OVERRIDES, SCENARIOS, run_experiments
from src.forecasting import generate_inputs
from src.households import generate_households
from src.metrics import calculate_metrics
from src.simulator import run_simulation


def test_scenario_l_combines_f_and_k_without_changing_earlier_scenarios():
    assert SCENARIOS["L"] == SCENARIOS["F"] == (True, True, "p2p_priority")
    assert REGULATOR_OVERRIDES["L"] == REGULATOR_OVERRIDES["K"] == {"reward_mode": "budget_sized"}
    assert "F" not in REGULATOR_OVERRIDES
    assert SCENARIOS["K"] == SCENARIOS["B"]
    assert list(SCENARIOS)[:11] == list("ABCDEFGHIJK")


@pytest.fixture(scope="module")
def runs():
    config = load_configuration(None)
    settings = config["simulation"]
    households = generate_households(settings, config["households"], config["buildings"])
    inputs = generate_inputs(households, settings, config["forecast"])
    settings = replace(settings, household_count=len(households))
    results = {}
    for name in "FKL":
        battery, regulated, strategy = SCENARIOS[name]
        results[name] = run_simulation(
            households, inputs, settings, config["market"], name, batteries_enabled=battery,
            regulation_enabled=regulated, regulator_settings=replace(config["regulator"], **REGULATOR_OVERRIDES.get(name, {})),
            blockchain_settings=config["blockchain"], battery_strategy=strategy)
    return households, results


def test_l_shares_f_physics_before_trading(runs):
    _, results = runs
    f, l = calculate_metrics(results["F"]), calculate_metrics(results["L"])
    for key in ("pv_generation_kwh", "demand_kwh", "surplus_available_after_self_balancing_kwh",
                "pv_surplus_before_battery_charging_kwh", "battery_initial_stored_kwh"):
        assert l[key] == pytest.approx(f[key])
    assert results["L"].battery_strategy == "p2p_priority"
    assert results["L"].regulator.settings.reward_mode == "budget_sized"


def test_l_energy_and_money_reconcile(runs):
    _, results = runs
    m = calculate_metrics(results["L"])  # raises if either reconciliation fails
    assert abs(m["energy_reconciliation_error_kwh"]) < 1e-7
    assert abs(m["financial_reconciliation_error_eur"]) < 1e-7
    # Meters + regulator equals the net payment to the external grid.
    assert m["community_including_regulator_net_cost_eur"] == pytest.approx(m["external_grid_net_cost_eur"])
    assert m["regulator_remaining_funds_eur"] == pytest.approx(
        m["regulator_initial_funds_eur"] + m["regulator_fee_revenue_eur"] - m["regulator_reward_expenditure_eur"])


def test_l_regulator_never_spends_money_it_does_not_hold(runs):
    _, results = runs
    regulator = results["L"].regulator
    max_rate = regulator.settings.max_reward_eur_kwh
    for hour in regulator.history:
        assert 0 <= hour["reward_rate_eur_kwh"] <= max_rate + 1e-12
        assert hour["reward_paid_eur"] <= hour["opening_funds_eur"] + 1e-9
        assert hour["closing_funds_eur"] >= -1e-9
    assert all(r.status in {"paid", "released"} for r in regulator.reservations)
    paid = sum(r.amount_eur for r in regulator.reservations if r.status == "paid")
    rewards = sum(t.reward_eur for t in results["L"].transactions)
    assert paid == pytest.approx(rewards)
    assert all(t.reward_eur == 0 for t in results["L"].transactions if t.market != "p2p")


def test_l_battery_limits_and_pv_only_charging(runs):
    households, results = runs
    specs = {h.household_id: h.battery for h in households if h.battery}
    for b in results["L"].balances:
        if b.soc is None:
            assert b.charge_kwh == b.discharge_kwh == 0
            continue
        spec = specs[b.household_id]
        assert spec.min_soc - 1e-9 <= b.soc <= spec.max_soc + 1e-9
        assert not (b.charge_kwh > 1e-9 and b.discharge_kwh > 1e-9)
        # Deferred charging only stores the meter's own PV surplus.
        assert b.charge_kwh <= b.pv_surplus_before_charging_kwh + 1e-9
        assert b.charge_kwh <= spec.max_charge_power_kw + 1e-9


def test_l_blockchain_records_every_internal_trade_once(runs):
    _, results = runs
    result = results["L"]
    internal = [t.transaction_id for t in result.transactions if t.market in {"p2p", "aggregator"}]
    recorded = [r["transaction_id"] for block in result.blockchain.blocks for r in block.transactions]
    assert len(result.blockchain.blocks) == 24
    assert sorted(recorded) == sorted(internal) and len(set(recorded)) == len(recorded)
    assert result.blockchain.validate(result.transactions, 24)


def test_l_runs_from_the_experiment_runner_on_shared_inputs(tmp_path):
    comparison = run_experiments(load_configuration(None), tmp_path, ["F", "K", "L"], charts=False)
    assert len({s["input_sha256"] for s in comparison["scenarios"]}) == 1
    l = next(s for s in comparison["scenarios"] if s["scenario"] == "L")
    assert l["battery_strategy"] == "p2p_priority"
    assert l["configuration"]["regulator"]["reward_mode"] == "budget_sized"
    assert (tmp_path / "L" / "summary.json").exists()
    assert "Combined scenario L" in (tmp_path / "discussion.md").read_text()


def test_robustness_win_rates_respect_kpi_direction():
    from scripts.robustness import KPIS, SCENARIOS, summarize
    rows = []
    for seed, (l_p2p, l_cost) in enumerate([(110, 90), (90, 110), (100, 100)]):
        for name in SCENARIOS:
            p2p, cost = (l_p2p, l_cost) if name == "L" else (100, 100)
            rows += [{"seed": seed, "condition": c, "scenario": name, **{k: 0.0 for k in KPIS},
                      "p2p_energy_kwh": p2p, "community_cost_storage_adjusted_eur": cost,
                      "p2p_share_of_surplus_pct": 0.0, "regulator_fee_revenue_eur": 0.0,
                      "regulator_reward_expenditure_eur": 0.0, "regulator_remaining_funds_eur": 0.0,
                      "battery_final_stored_kwh": 0.0, "battery_loss_kwh": 0.0}
                     for c in ("fixed", "demand_response")]
    _, wins = summarize(rows, [0, 1, 2])
    w = {(r["condition"], r["comparison"], r["kpi"]): r for r in wins}
    p2p = w["fixed", "L vs F", "p2p_energy_kwh"]
    cost = w["fixed", "L vs F", "community_cost_storage_adjusted_eur"]
    assert p2p["l_better_pct"] == pytest.approx(100 / 3) and p2p["tie_pct"] == pytest.approx(100 / 3)
    assert cost["l_better_pct"] == pytest.approx(100 / 3) and cost["l_worse_pct"] == pytest.approx(100 / 3)
