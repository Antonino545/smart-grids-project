"""Keep the team's PDF parameter reference aligned with configuration."""

import json
from pathlib import Path

import pytest

from scripts.report_parameters import get_value, parameter_paths


def configuration():
    return json.loads((Path(__file__).resolve().parents[1] / "config/default.json").read_text())


def test_reference_covers_every_default_parameter():
    paths = parameter_paths(configuration())
    assert len(paths) == 155
    assert "buildings.types.school.weekend_multiplier" in paths
    assert "simulation.battery.charge_efficiency" in paths


def test_new_parameter_requires_documentation():
    config = configuration()
    config["forecast"]["undocumented_parameter"] = 1
    with pytest.raises(ValueError, match="forecast.undocumented_parameter"):
        parameter_paths(config)


def test_removed_parameter_rejects_stale_documentation():
    config = configuration()
    del config["simulation"]["random_seed"]
    with pytest.raises(ValueError, match="simulation.random_seed"):
        parameter_paths(config)


def test_values_follow_supplied_configuration_and_ignore_experiment_metadata():
    config = configuration()
    config["simulation"]["hours"] = 168
    config["experiment"] = {"scenario": "A", "batteries_enabled": True}
    assert get_value(config, "simulation.hours") == 168
    assert len(parameter_paths(config)) == 155
