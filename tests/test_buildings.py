from collections import Counter
from dataclasses import replace
from random import Random

import pytest

from config.buildings import BuildingSettings, load_building_settings
from config.settings import HouseholdSettings, SimulationSettings
from main import load_configuration
from src.building_profiles import building_attributes
from src.forecasting import generate_inputs
from src.households import generate_households


def test_building_composition_one_roof_and_fixed_battery_identity():
    settings = SimulationSettings()
    buildings = generate_households(settings)
    assert Counter(b.building_type for b in buildings) == {
        "small_house": 50, "apartment_block": 30, "supermarket": 10, "school": 10}
    for group in range(1, 11):
        assert Counter(b.building_type for b in buildings if b.group_id == group) == {
            "small_house": 5, "apartment_block": 3, "supermarket": 1, "school": 1}
    legacy = generate_households(settings, buildings=BuildingSettings(enabled=False))
    assert {b.household_id for b in buildings if b.has_battery} == {b.household_id for b in legacy if b.has_battery}
    assert buildings == generate_households(settings)
    for b in buildings:
        assert b.floor_area_m2 == pytest.approx(b.roof_area_m2 * b.floors)
        assert b.pv_capacity_kw <= b.roof_area_m2 * b.usable_roof_fraction * .2 + 1e-9
        if b.building_type == "apartment_block":
            assert b.dwelling_units >= b.floors * 2
        if b.battery:
            scale = BuildingSettings().types[b.building_type].battery_scale
            assert b.battery.capacity_kwh == settings.battery.capacity_kwh * scale


def test_more_floors_do_not_create_more_roof_or_pv():
    base = BuildingSettings()
    def attributes(floors):
        spec = replace(base.types["apartment_block"], floors_min=floors, floors_max=floors,
                       units_per_floor_min=3, units_per_floor_max=3,
                       roof_min_m2=250, roof_max_m2=250,
                       roof_usable_fraction_min=.5, roof_usable_fraction_max=.5)
        config = replace(base, types={**base.types, "apartment_block": spec})
        return building_attributes("apartment_block", config, HouseholdSettings(), None, Random(5))
    low, high = attributes(4), attributes(8)
    assert low["roof_area_m2"] == high["roof_area_m2"] == 250
    assert low["pv_capacity_kw"] == high["pv_capacity_kw"] == 25
    assert high["dwelling_units"] == 2 * low["dwelling_units"]
    assert sum(high["demand_profile_kwh"]) == pytest.approx(2 * sum(low["demand_profile_kwh"]))


def test_type_load_shapes_and_weekend_calendar_effect():
    settings = SimulationSettings(hours=7 * 24)
    buildings = generate_households(settings)
    records = generate_inputs(buildings, settings)
    for b in buildings:
        day = b.demand_profile_kwh
        assert min(day) >= 0
        if b.building_type in {"school", "supermarket"}:
            assert day[12] > day[2] * 2
        if b.building_type == "supermarket":
            assert day[2] > 0  # Refrigeration/base loads continue while closed.
        if b.building_type == "school":
            weekday = sum(r.demand_kwh for r in records if r.household_id == b.household_id and r.hour < 24)
            weekend = sum(r.demand_kwh for r in records if r.household_id == b.household_id and 5 * 24 <= r.hour < 6 * 24)
            assert weekend < weekday * .25
    assert records == generate_inputs(buildings, settings)
    assert any(sum(r.demand_kwh for r in records if r.household_id == b.household_id and r.hour < 24)
               != sum(r.demand_kwh for r in records if r.household_id == b.household_id and 24 <= r.hour < 48)
               for b in buildings)


def test_partial_building_configuration_and_invalid_shares(tmp_path):
    import json
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"buildings": {"types": {"school": {"weekend_multiplier": .1}}}}))
    config = load_configuration(path)
    assert config["buildings"].types["school"].weekend_multiplier == .1
    assert config["buildings"].types["school"].roof_min_m2 == 700
    for override in ({"types": {"unknown": {}}}, {"types": {"school": {"share": .4}}},
                     {"pv_density_kw_m2": float("nan")}, {"types": {"school": {"roof_min_m2": -1}}}):
        with pytest.raises((ValueError, TypeError)):
            load_building_settings(override)


def test_building_profile_chart_means_reconcile_with_total_energy():
    from src.building_charts import building_chart_data
    settings = SimulationSettings()
    buildings = generate_households(settings)
    inputs = generate_inputs(buildings, settings)
    hourly, types = building_chart_data(buildings, inputs)
    assert len(hourly) == 4 * 24
    assert sum(row["count"] for row in types) == 100
    assert sum(row["battery_count"] for row in types) == 55
    assert sum(row["mean_demand_kwh"] * row["building_count"] for row in hourly) == pytest.approx(sum(r.demand_kwh for r in inputs))
    assert sum(row["mean_pv_kwh"] * row["building_count"] for row in hourly) == pytest.approx(sum(r.pv_kwh for r in inputs))


def test_legacy_configuration_reproduces_original_energy_volumes():
    from src.metrics import calculate_metrics
    from src.simulator import run_simulation
    settings = SimulationSettings()
    buildings = generate_households(settings, buildings=BuildingSettings(enabled=False))
    result = run_simulation(buildings, generate_inputs(buildings, settings), settings, blockchain_enabled=False)
    metrics = calculate_metrics(result)
    assert metrics["p2p_energy_kwh"] == pytest.approx(8.934787197836283)
    assert metrics["pv_generation_kwh"] == pytest.approx(2655.4480549034593)
