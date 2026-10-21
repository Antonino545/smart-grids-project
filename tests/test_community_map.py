from collections import Counter
import csv

import pytest

from config.settings import SimulationSettings
from src.community_map import community_layout, generate_community_map
from src.households import generate_households


def test_square_layout_preserves_every_household_and_real_attributes():
    households = generate_households(SimulationSettings())
    cells = community_layout(households)
    assert cells == community_layout(list(reversed(households)))
    assert len(cells) == len({(c["row"], c["column"]) for c in cells}) == 100
    assert {c["row"] for c in cells} == {c["column"] for c in cells} == set(range(10))
    lookup = {h.household_id: h for h in households}
    for cell in cells:
        h = lookup[cell["household_id"]]
        assert cell["group_id"] == cell["row"] + 1 == h.group_id
        assert cell["has_battery"] == h.has_battery
        assert cell["pv_capacity_kw"] == h.pv_capacity_kw
    assert sum(c["has_battery"] for c in cells) == 55
    assert Counter(c["row"] for c in cells) == dict.fromkeys(range(10), 10)


def test_map_renders_and_csv_counts_match_actual_ownership(tmp_path):
    households = generate_households(SimulationSettings())
    before = list(households)
    generate_community_map(households, tmp_path)
    assert households == before
    for extension in ("png", "svg"):
        assert (tmp_path / f"community_map.{extension}").stat().st_size > 1000
    with (tmp_path / "data/neighborhood_distribution.csv").open() as handle:
        groups = list(csv.DictReader(handle))
    assert len(groups) == 10
    assert sum(int(g["battery_count"]) for g in groups) == 55
    assert sum(int(g["pv_only_count"]) for g in groups) == 45
    assert {int(g["battery_count"]) for g in groups} == {5, 6}


def test_layout_handles_other_group_sizes_and_rejects_duplicate_ids():
    households = generate_households(SimulationSettings(household_count=6, group_count=2, battery_household_count=3))
    cells = community_layout(households)
    assert {(c["row"], c["column"]) for c in cells} == {(r, c) for r in range(2) for c in range(3)}
    with pytest.raises(ValueError, match="unique"):
        community_layout(households + [households[0]])


def test_simulation_command_generates_map_from_its_own_households(tmp_path):
    import subprocess
    import sys
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [sys.executable, str(project_root / "main.py"), "--scenario", "B", "--output", str(tmp_path)],
        cwd=project_root, capture_output=True, text=True,
    )
    assert completed.returncode == 0, completed.stderr
    for suffix in ("png", "svg"):
        assert (tmp_path / "charts" / f"community_map.{suffix}").stat().st_size > 1000
    with (tmp_path / "inputs" / "households.csv").open() as handle:
        households = {row["household_id"]: row for row in csv.DictReader(handle)}
    with (tmp_path / "charts" / "data" / "community_layout.csv").open() as handle:
        cells = list(csv.DictReader(handle))
    assert len(cells) == len(households) == 150
    for cell in cells:
        household = households[cell["household_id"]]
        assert cell["group_id"] == household["group_id"]
        assert cell["has_battery"] == household["has_battery"]
        assert cell["pv_capacity_kw"] == household["pv_capacity_kw"]
