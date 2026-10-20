from dataclasses import replace

import pytest

from config.settings import BatterySettings, SimulationSettings
from src.balancing import self_balance
from src.battery import BatteryState
from src.forecasting import generate_inputs
from src.households import generate_households


def test_battery_power_soc_and_losses():
    state = BatteryState.initialize(BatterySettings())
    before = state.stored_kwh
    flow = state.operate(100)
    assert flow.charge_kwh == 3
    assert state.stored_kwh == pytest.approx(before + 3 * 0.95)
    for _ in range(10):
        state.operate(100)
    assert state.soc == pytest.approx(0.9)
    for _ in range(10):
        state.operate(-100)
    assert state.soc == pytest.approx(0.1)
    assert state.operate(-1).discharge_kwh == pytest.approx(0)


def test_complete_day_self_balancing_conserves_energy():
    settings = SimulationSettings()
    households = generate_households(settings)
    batteries = {h.household_id: BatteryState.initialize(h.battery) for h in households if h.battery}
    assert len(batteries) == 55
    records = generate_inputs(households, settings)
    previous = {key: state.stored_kwh for key, state in batteries.items()}
    results = []
    for record in records:
        battery = batteries.get(record.household_id)
        result = self_balance(record, battery)
        results.append(result)
        result.verify()
        if battery:
            assert result.stored_start_kwh == pytest.approx(previous[record.household_id])
            assert 0.1 - 1e-10 <= result.soc <= 0.9 + 1e-10
            assert result.charge_kwh <= 3 and result.discharge_kwh <= 3
            previous[record.household_id] = result.stored_end_kwh
        else:
            assert result.charge_kwh == result.discharge_kwh == result.battery_loss_kwh == 0
    assert sum(r.battery_loss_kwh for r in results) > 0
    assert len(results) == 2400


def test_battery_cannot_export_stored_energy():
    settings = SimulationSettings()
    record = generate_inputs(generate_households(settings), settings)[0]
    battery = BatteryState.initialize(BatterySettings())
    result = self_balance(replace(record, pv_kwh=0, demand_kwh=0.1), battery)
    assert result.discharge_kwh == pytest.approx(0.1)
    assert result.balance_kwh == pytest.approx(0)


def test_p2p_priority_sells_only_pv_before_charging():
    from src.forecasting import HourlyInput
    from src.households import Household
    from src.simulator import run_simulation
    settings = SimulationSettings(household_count=2, group_count=1, battery_household_count=1, hours=1)
    households = [Household("S", 1, 5, BatterySettings(), (0,) * 24, 1, .7),
                  Household("B", 1, 2, None, (0,) * 24, 1.5, 1)]
    def record(name, pv, demand):
        return HourlyInput(0, "2026-06-15T12:00:00+02:00", name, 900, pv, demand, .2,
                           "synthetic", "synthetic", "synthetic")
    inputs = [record("S", 3, 0), record("B", 0, 3)]
    first = run_simulation(households, inputs, settings, blockchain_enabled=False)
    priority = run_simulation(households, inputs, settings, blockchain_enabled=False, battery_strategy="p2p_priority")
    assert sum(t.quantity_kwh for t in first.transactions if t.market == "p2p") == 0
    assert sum(t.quantity_kwh for t in priority.transactions if t.market == "p2p") == 3
    assert priority.balances[0].charge_kwh == priority.balances[0].discharge_kwh == 0
    assert priority.balances[0].stored_start_kwh == priority.balances[0].stored_end_kwh
    assert first.balances[0].charge_kwh == 3
