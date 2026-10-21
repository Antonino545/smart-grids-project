from dataclasses import replace
import json

import pytest

from main import load_configuration
from scripts.verify_results import verify_results
from src.experiments import run_experiments


def test_exported_artifacts_verify_and_detect_altered_inputs(tmp_path):
    config = load_configuration(None)
    config["simulation"] = replace(config["simulation"], household_count=4, group_count=2, battery_household_count=2)
    results = tmp_path / "results"
    run_experiments(config, results, ["A", "B"], charts=False)
    assert set(verify_results(results)) == {"A", "B"}
    path = results / "inputs" / "hourly_inputs.csv"
    path.write_text(path.read_text().replace("synthetic_building_profile", "altered", 1))
    with pytest.raises(ValueError, match="recorded hash"):
        verify_results(results)
