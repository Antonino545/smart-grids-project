"""Step 1 checks for configuration and the actual command-line entry point."""

from pathlib import Path
import random
import subprocess
import sys

import pytest

from config.settings import BatterySettings, SimulationSettings


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_default_community_configuration():
    settings = SimulationSettings()
    assert settings.household_count == 100
    assert settings.group_count == 10
    assert settings.households_per_group == 10
    assert settings.battery_household_count == 55
    assert settings.hours == 24
    assert settings.timestep_hours == 1.0


def test_randomness_is_repeatable_and_does_not_change_global_state():
    settings = SimulationSettings()
    global_state = random.getstate()
    first = settings.create_random_generator()
    second = settings.create_random_generator()
    assert [first.random() for _ in range(10)] == [second.random() for _ in range(10)]
    assert random.getstate() == global_state


@pytest.mark.parametrize("overrides", [
    {"household_count": 0}, {"group_count": 0}, {"group_count": 3},
    {"battery_household_count": 101}, {"battery_household_count": -1},
    {"hours": 0}, {"timestep_hours": 0}, {"hours": 1.5},
    {"log_level": "INVALID"},
])
def test_invalid_simulation_configuration_is_rejected(overrides):
    with pytest.raises(ValueError):
        SimulationSettings(**overrides)


@pytest.mark.parametrize("overrides", [
    {"capacity_kwh": 0}, {"max_charge_power_kw": -1},
    {"charge_efficiency": 0}, {"discharge_efficiency": 1.1},
    {"initial_soc": 0.95}, {"min_soc": -0.1},
    {"strategy": "grid_arbitrage"},
])
def test_invalid_battery_configuration_is_rejected(overrides):
    with pytest.raises(ValueError):
        BatterySettings(**overrides)


def test_entry_point_runs_successfully(tmp_path):
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "main.py"), "--output", str(tmp_path), "--scenario", "A", "--no-charts"],
        cwd=PROJECT_ROOT, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Simulation A complete" in result.stderr
    assert "100 households" in result.stderr


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_settings_are_rejected(value):
    with pytest.raises(ValueError):
        BatterySettings(capacity_kwh=value)
    with pytest.raises(ValueError):
        SimulationSettings(timestep_hours=value)
