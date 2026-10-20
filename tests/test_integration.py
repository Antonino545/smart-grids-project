import csv
import json

import pytest

from config.settings import SimulationSettings
from src.forecasting import generate_inputs
from src.households import generate_households
from src.metrics import calculate_metrics
from src.output import export_result
from src.simulator import run_simulation


def test_end_to_end_regulated_day_exports_and_kpis(tmp_path):
    settings = SimulationSettings()
    households = generate_households(settings)
    inputs = generate_inputs(households, settings)
    result = run_simulation(households, inputs, settings, name="B", regulation_enabled=True)
    metrics = calculate_metrics(result)
    assert metrics["block_count"] == 24 and metrics["blockchain_valid"]
    assert 0 <= metrics["p2p_share_pct"] <= 100
    assert metrics["p2p_share_pct"] == pytest.approx(100 * metrics["p2p_energy_kwh"] / result.surplus_available_kwh)
    assert metrics["community_including_regulator_net_cost_eur"] == pytest.approx(metrics["external_grid_net_cost_eur"])
    assert metrics["energy_reconciliation_error_kwh"] == pytest.approx(0, abs=1e-8)
    assert metrics["financial_reconciliation_error_eur"] == pytest.approx(0, abs=1e-8)
    export_result(result, inputs, tmp_path)
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary["metrics"] == metrics
    assert len(list(csv.DictReader((tmp_path / "household_hourly.csv").open()))) == 2400
    chain = json.loads((tmp_path / "blockchain.json").read_text())
    recorded = [t for b in chain["blocks"] for t in b["transactions"]]
    assert len(recorded) == sum(t.market != "grid" for t in result.transactions)
