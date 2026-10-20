import pytest

from main import load_configuration
from src.charts import generate_charts
from src.experiments import SCENARIOS
from src.forecasting import generate_inputs
from src.households import generate_households
from src.metrics import calculate_metrics
from src.result_charts import prepare_chart_data
from src.simulator import run_simulation


@pytest.fixture(scope="module")
def results():
    config = load_configuration(None)
    settings = config["simulation"]
    households = generate_households(settings)
    inputs = generate_inputs(households, settings)
    return [run_simulation(households, inputs, settings, name=name,
                           batteries_enabled=battery, regulation_enabled=regulated,
                           battery_strategy=strategy, blockchain_enabled=False)
            for name, (battery, regulated, strategy) in SCENARIOS.items()]


def test_chart_data_reconciles_with_accounting(results):
    data = prepare_chart_data(results)
    for result in results:
        metric = calculate_metrics(result)
        rows = [r for r in data["hourly_profiles"] if r["scenario"] == result.name]
        assert len(rows) == 24
        assert sum(r["p2p_kwh"] for r in rows) == pytest.approx(metric["p2p_energy_kwh"])
        assert sum(r["grid_imports_kwh"] for r in rows) == pytest.approx(metric["grid_imports_kwh"])
        destination = next(r for r in data["surplus_destinations"] if r["scenario"] == result.name)
        assert sum(destination[k] for k in ("p2p_kwh", "aggregator_kwh", "grid_exports_kwh", "deferred_charge_kwh")) == pytest.approx(destination["offered_surplus_kwh"])
        costs = [r for r in data["household_cost_distribution"] if r["scenario"] == result.name]
        assert len(costs) == 100
        assert sum(r["net_cost_eur"] for r in costs) == pytest.approx(metric["household_net_cost_eur"])
        flow = next(r for r in data["battery_energy_flows"] if r["scenario"] == result.name)
        assert flow["charge_kwh"] - flow["discharge_kwh"] - flow["loss_kwh"] == pytest.approx(flow["stored_change_kwh"])
    assert len(data["regulation_effects"]) == 3
    assert data["regulation_effects"][0]["p2p_change_kwh"] == pytest.approx(calculate_metrics(results[1])["p2p_energy_kwh"] - calculate_metrics(results[0])["p2p_energy_kwh"])


def test_all_chart_files_render_and_data_exports_exist(results, tmp_path):
    generate_charts(results, tmp_path)
    for name in prepare_chart_data(results):
        for suffix in ("png", "svg"):
            assert (tmp_path / f"{name}.{suffix}").stat().st_size > 1000
        assert (tmp_path / "data" / f"{name}.csv").stat().st_size > 20


def test_single_unregulated_scenario_has_no_fabricated_comparison(results):
    data = prepare_chart_data([results[0]])
    assert data["regulation_effects"] == []
