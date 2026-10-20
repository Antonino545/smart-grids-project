import pytest

from main import load_configuration
from src.experiments import run_experiments
from src.forecasting import generate_inputs
from src.households import generate_households
from src.metrics import calculate_metrics
from src.simulator import run_simulation


def test_shared_inputs_counterfactuals_and_strategies(tmp_path):
    comparison = run_experiments(load_configuration(None), tmp_path, list("ABCDEF"), charts=False)
    summaries = {s["scenario"]: s for s in comparison["scenarios"]}
    assert len({s["input_sha256"] for s in summaries.values()}) == 1
    for name, summary in summaries.items():
        m = summary["metrics"]
        assert m["block_count"] == 24 and m["blockchain_valid"]
        assert m["active_battery_count"] == (0 if name in "CD" else 55)
        assert abs(m["energy_reconciliation_error_kwh"]) < 1e-7
        if name in "CD":
            assert m["battery_charge_kwh"] == m["battery_discharge_kwh"] == 0
    assert summaries["A"]["metrics"]["pv_generation_kwh"] == summaries["C"]["metrics"]["pv_generation_kwh"]
    assert summaries["A"]["metrics"]["demand_kwh"] == summaries["C"]["metrics"]["demand_kwh"]
    assert summaries["E"]["battery_strategy"] == "p2p_priority"


def test_zero_surplus_ratios_are_undefined():
    from dataclasses import replace
    config = load_configuration(None)
    settings = config["simulation"]
    households = generate_households(settings)
    inputs = [replace(row, pv_kwh=0) for row in generate_inputs(households, settings)]
    result = run_simulation(households, inputs, settings, batteries_enabled=False)
    metrics = calculate_metrics(result)
    assert metrics["p2p_share_pct"] is None
    assert metrics["p2p_to_grid_exports_ratio"] is None
    assert metrics["p2p_energy_kwh"] == 0
