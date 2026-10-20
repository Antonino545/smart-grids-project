"""Deterministic community generation; ownership stays fixed across experiments."""

import csv
import json
from dataclasses import asdict, dataclass
from math import exp
from pathlib import Path

from config.settings import BatterySettings, HouseholdSettings, SimulationSettings


@dataclass(frozen=True)
class Household:
    household_id: str
    group_id: int
    pv_capacity_kw: float
    battery: BatterySettings | None
    demand_profile_kwh: tuple[float, ...]
    bid_multiplier: float
    ask_multiplier: float

    @property
    def has_battery(self) -> bool:
        return self.battery is not None


def generate_households(
    settings: SimulationSettings, parameters: HouseholdSettings | None = None,
) -> list[Household]:
    parameters = parameters or HouseholdSettings()
    rng = settings.create_random_generator()
    per_group, remainder = divmod(settings.battery_household_count, settings.group_count)
    extra_groups = set(rng.sample(range(settings.group_count), remainder))
    owners = set()
    for group in range(settings.group_count):
        indices = range(group * settings.households_per_group, (group + 1) * settings.households_per_group)
        owners.update(rng.sample(list(indices), per_group + (group in extra_groups)))
    households = []
    for index in range(settings.household_count):
        daily_demand = rng.uniform(parameters.daily_demand_min_kwh, parameters.daily_demand_max_kwh)
        shift = rng.uniform(-parameters.profile_shift_max_hours, parameters.profile_shift_max_hours)
        weights = [
            (parameters.base_demand_weight
             + parameters.morning_peak_weight * exp(-((hour - parameters.morning_peak_hour - shift)
                                                     / parameters.morning_peak_width_hours) ** 2)
             + parameters.evening_peak_weight * exp(-((hour - parameters.evening_peak_hour - shift)
                                                     / parameters.evening_peak_width_hours) ** 2))
            * rng.uniform(1 - parameters.profile_noise_fraction, 1 + parameters.profile_noise_fraction)
            for hour in range(24)
        ]
        profile = tuple(daily_demand * weight / sum(weights) for weight in weights)
        households.append(Household(
            household_id=f"H{index + 1:03d}",
            group_id=index // settings.households_per_group + 1,
            pv_capacity_kw=rng.uniform(parameters.pv_capacity_min_kw, parameters.pv_capacity_max_kw),
            battery=settings.battery if index in owners else None,
            demand_profile_kwh=profile,
            bid_multiplier=rng.uniform(parameters.bid_multiplier_min, parameters.bid_multiplier_max),
            ask_multiplier=rng.uniform(parameters.ask_multiplier_min, parameters.ask_multiplier_max),
        ))
    return households


def export_households(households: list[Household], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for household in households:
        row = {
            "household_id": household.household_id, "group_id": household.group_id,
            "pv_capacity_kw": household.pv_capacity_kw, "has_battery": household.has_battery,
            "bid_multiplier": household.bid_multiplier, "ask_multiplier": household.ask_multiplier,
            "demand_profile_kwh": json.dumps(household.demand_profile_kwh),
        }
        row.update({f"battery_{key}": value for key, value in asdict(BatterySettings()).items()})
        if household.battery:
            row.update({f"battery_{key}": value for key, value in asdict(household.battery).items()})
        else:
            for key in asdict(BatterySettings()):
                row[f"battery_{key}"] = ""
        rows.append(row)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
