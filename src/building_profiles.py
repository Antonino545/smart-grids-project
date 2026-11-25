"""Seeded building geometry and synthetic hourly loads for aggregate meter participants."""

from dataclasses import replace
from math import exp
from random import Random

from config.buildings import BuildingSettings
from config.settings import BatterySettings, HouseholdSettings, SimulationSettings

TYPE_LABELS = {"small_house": "Small house", "apartment_block": "Apartment block",
               "supermarket": "Supermarket", "school": "School", "legacy_house": "Legacy house"}
TYPE_SHORT_LABELS = {"small_house": "HOUSE", "apartment_block": "BLOCK",
                    "supermarket": "SHOP", "school": "SCHOOL", "legacy_house": "HOUSE"}

LIVING_AREA_FRACTION = 0.80


def assign_building_types(settings: SimulationSettings, buildings: BuildingSettings) -> list[str]:
    """Community-wide largest-remainder allocation, dealt round-robin across groups.

    Allocating over the whole community lets a type have fewer buildings than there are
    groups (e.g. 4 schools for 10 groups); round-robin dealing keeps every group at the
    same size and spreads each type as evenly as possible. Positions are then shuffled.
    """
    rng = Random(settings.random_seed + 3000)
    exact = {name: spec.share * settings.household_count for name, spec in buildings.types.items()}
    counts = {name: int(value) for name, value in exact.items()}
    remainder = settings.household_count - sum(counts.values())
    ordered = sorted(exact, key=lambda name: (-(exact[name] - counts[name]), name))
    for name in ordered[:remainder]:
        counts[name] += 1
    pool = [name for name in buildings.types for _ in range(counts[name])]
    groups = [[] for _ in range(settings.group_count)]
    for index, name in enumerate(pool):
        groups[index % settings.group_count].append(name)
    assigned = []
    for group in groups:
        rng.shuffle(group)
        assigned.extend(group)
    return assigned


def roof_pv_capacity(roof_area_m2: float, usable_fraction: float, density_kw_m2: float, limit_kw: float) -> float:
    """A building has one roof. Floors and home counts deliberately do not enter."""
    return min(roof_area_m2 * usable_fraction * density_kw_m2, limit_kw)


def building_attributes(kind: str, buildings: BuildingSettings, parameters: HouseholdSettings,
                        base_battery: BatterySettings | None, rng: Random) -> dict:
    spec = buildings.types[kind]
    roof_area = rng.uniform(spec.roof_min_m2, spec.roof_max_m2)
    floors = rng.randint(spec.floors_min, spec.floors_max)
    if kind == "apartment_block":
        # Homes follow from the footprint: 80 % of each floor is living space, the rest is
        # walls, stairs and the lift. Each home's size is drawn from the Turin-like range.
        home_area = rng.uniform(spec.home_area_m2_min, spec.home_area_m2_max)
        homes = floors * max(1, round(roof_area * LIVING_AREA_FRACTION / home_area))
    else:
        homes = 1 if kind == "small_house" else 0
    floor_area = roof_area * floors
    usable_fraction = rng.uniform(spec.roof_usable_fraction_min, spec.roof_usable_fraction_max)
    energy_unit = rng.uniform(spec.daily_energy_min, spec.daily_energy_max)
    daily_energy = energy_unit * (homes if spec.energy_basis == "per_home" else floor_area)
    shift = rng.uniform(-parameters.profile_shift_max_hours, parameters.profile_shift_max_hours)

    def weights(weekend: bool):
        result = []
        for hour in range(24):
            if spec.profile == "residential":
                weight = (spec.base_load_weight
                          + parameters.morning_peak_weight * exp(-((hour - parameters.morning_peak_hour - shift)
                                                                  / parameters.morning_peak_width_hours) ** 2)
                          + parameters.evening_peak_weight * exp(-((hour - parameters.evening_peak_hour - shift)
                                                                  / parameters.evening_peak_width_hours) ** 2))
            else:
                operating = spec.opening_hour <= hour < spec.closing_hour and (not weekend or spec.weekend_open)
                weight = spec.base_load_weight + spec.operating_load_weight * operating
            result.append(weight * rng.uniform(1 - parameters.profile_noise_fraction, 1 + parameters.profile_noise_fraction))
        return result

    weekday_weights, weekend_weights = weights(False), weights(True)
    battery = replace(base_battery,
                      capacity_kwh=base_battery.capacity_kwh * spec.battery_scale,
                      max_charge_power_kw=base_battery.max_charge_power_kw * spec.battery_scale,
                      max_discharge_power_kw=base_battery.max_discharge_power_kw * spec.battery_scale) if base_battery else None
    return {
        "building_type": kind, "roof_area_m2": roof_area, "floors": floors,
        "floor_area_m2": floor_area, "homes": homes, "usable_roof_fraction": usable_fraction,
        "panel_tilt_deg": spec.panel_tilt_deg, "panel_azimuth_deg": spec.panel_azimuth_deg,
        "pv_capacity_kw": roof_pv_capacity(roof_area, usable_fraction, buildings.pv_density_kw_m2, spec.pv_limit_kw),
        "battery": battery,
        "demand_profile_kwh": tuple(daily_energy * w / sum(weekday_weights) for w in weekday_weights),
        "weekend_demand_profile_kwh": tuple(daily_energy * spec.weekend_multiplier * w / sum(weekend_weights)
                                            for w in weekend_weights),
        "daily_variation_fraction": spec.daily_variation_fraction,
    }
