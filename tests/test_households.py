from collections import Counter
import csv

from config.settings import SimulationSettings
from src.households import export_households, generate_households


def test_complete_reproducible_community(tmp_path):
    households = generate_households(SimulationSettings())
    assert households == generate_households(SimulationSettings())
    assert len(households) == len({h.household_id for h in households}) == 100
    assert Counter(h.group_id for h in households) == dict.fromkeys(range(1, 11), 10)
    assert sum(h.has_battery for h in households) == 55
    assert sum(not h.has_battery for h in households) == 45
    assert all(h.pv_capacity_kw > 0 for h in households)
    assert all(len(h.demand_profile_kwh) == 24 and min(h.demand_profile_kwh) >= 0 for h in households)
    counts = Counter(h.group_id for h in households if h.has_battery)
    assert set(counts.values()) == {5, 6}
    path = tmp_path / "households.csv"
    export_households(households, path)
    with path.open() as handle:
        assert len(list(csv.DictReader(handle))) == 100
