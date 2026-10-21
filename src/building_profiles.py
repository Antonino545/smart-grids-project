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


def assign_building_types(settings: SimulationSettings, buildings: BuildingSettings) -> list[str]:
    """Largest-remainder allocation within each group, then a seeded shuffle of positions."""
    rng = Random(settings.random_seed + 3000)
    assigned = []
    for _ in range(settings.group_count):
        exact = {name: spec.share * settings.households_per_group for name, spec in buildings.types.items()}
        counts = {name: int(value) for name, value in exact.items()}
        remainder = settings.households_per_group - sum(counts.values())
        ordered = sorted(exact, key=lambda name: (-(exact[name] - counts[name]), name))
        for name in ordered[:remainder]:
            counts[name] += 1
        group = [name for name in buildings.types for _ in range(counts[name])]
        rng.shuffle(group)
        assigned.extend(group)
    return assigned


def roof_pv_capacity(roof_area_m2: float, usable_fraction: float, density_kw_m2: float, limit_kw: float) -> float:
    """A building has one roof. Floors and dwelling counts deliberately do not enter."""
    return min(roof_area_m2 * usable_fraction * density_kw_m2, limit_kw)


def building_attributes(kind: str, buildings: BuildingSettings, parameters: HouseholdSettings,
                        base_battery: BatterySettings | None, rng: Random) -> dict:
    spec = buildings.types[kind]
    roof_area = rng.uniform(spec.roof_min_m2, spec.roof_max_m2)
    floors = rng.randint(spec.floors_min, spec.floors_max)
    units_per_floor = rng.randint(spec.units_per_floor_min, spec.units_per_floor_max)
    units = floors * units_per_floor if kind == "apartment_block" else 1 if kind == "small_house" else 0
    floor_area = roof_area * floors
    usable_fraction = rng.uniform(spec.roof_usable_fraction_min, spec.roof_usable_fraction_max)
    energy_unit = rng.uniform(spec.daily_energy_min, spec.daily_energy_max)
    daily_energy = energy_unit * (units if spec.energy_basis == "per_dwelling" else floor_area)
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
        "floor_area_m2": floor_area, "dwelling_units": units, "usable_roof_fraction": usable_fraction,
        "pv_capacity_kw": roof_pv_capacity(roof_area, usable_fraction, buildings.pv_density_kw_m2, spec.pv_limit_kw),
        "battery": battery,
        "demand_profile_kwh": tuple(daily_energy * w / sum(weekday_weights) for w in weekday_weights),
        "weekend_demand_profile_kwh": tuple(daily_energy * spec.weekend_multiplier * w / sum(weekend_weights)
                                            for w in weekend_weights),
        "daily_variation_fraction": spec.daily_variation_fraction,
    }
