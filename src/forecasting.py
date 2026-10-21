"""Simple PV model and hourly historical price means with a strict forecast cutoff."""

import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from math import isfinite, pi, sin
from pathlib import Path
from random import Random

from config.settings import ForecastSettings, SimulationSettings
from src.households import Household


@dataclass(frozen=True)
class HourlyInput:
    hour: int
    timestamp: str
    household_id: str
    irradiance_w_m2: float
    pv_kwh: float
    demand_kwh: float
    reference_price_eur_kwh: float
    weather_source: str
    demand_source: str
    price_source: str

    def __post_init__(self) -> None:
        if type(self.hour) is not int or self.hour < 0:
            raise ValueError("Input hour must be a nonnegative integer.")
        if not self.household_id:
            raise ValueError("Input household ID cannot be empty.")
        if not all(isfinite(value) and value >= 0 for value in
                   (self.irradiance_w_m2, self.pv_kwh, self.demand_kwh)):
            raise ValueError("Input energy/weather must be finite and nonnegative.")
        if not isfinite(self.reference_price_eur_kwh):
            raise ValueError("Input reference price must be finite.")
        parse_timestamp(self.timestamp)


def parse_timestamp(value: str) -> datetime:
    timestamp = datetime.fromisoformat(value)
    if timestamp.tzinfo is None:
        raise ValueError("Input timestamps must include a UTC offset.")
    return timestamp


def hourly_price_forecast(history: list[tuple[datetime, float]], cutoff: datetime) -> dict[int, float]:
    """Exclude every observation at or after forecast issuance (even same-day data)."""
    prices: dict[int, list[float]] = {hour: [] for hour in range(24)}
    for timestamp, price in history:
        if timestamp.tzinfo is None or not isfinite(price):
            raise ValueError("Historical prices require aware timestamps and finite values.")
        if timestamp < cutoff:
            prices[timestamp.astimezone(cutoff.tzinfo).hour].append(price)
    if any(not values for values in prices.values()):
        raise ValueError("Historical prices before cutoff must cover every hour of day.")
    return {hour: sum(values) / len(values) for hour, values in prices.items()}


def pv_forecast(capacity_kw: float, irradiance_w_m2: float, performance_factor: float, timestep_hours: float) -> float:
    values = (capacity_kw, irradiance_w_m2, performance_factor, timestep_hours)
    if not all(isfinite(value) for value in values) or min(values) < 0:
        raise ValueError("PV inputs must be finite and nonnegative.")
    return min(capacity_kw, capacity_kw * irradiance_w_m2 / 1000 * performance_factor) * timestep_hours


def _read_csv(path: str) -> list[dict[str, str]]:
    with Path(path).open(newline="") as handle:
        return list(csv.DictReader(handle))


def _unique_mapping(rows, key_function, value_field):
    result = {}
    for row in rows:
        key = key_function(row)
        value = float(row[value_field])
        if key in result or not isfinite(value) or value < 0:
            raise ValueError("Duplicate timestamps/households or invalid energy/weather values in CSV.")
        result[key] = value
    return result


def generate_inputs(households: list[Household], settings: SimulationSettings,
                    forecast: ForecastSettings | None = None) -> list[HourlyInput]:
    forecast = forecast or ForecastSettings()
    # Hourly input records deliberately support one-hour steps only in this version.
    if settings.timestep_hours != 1:
        raise ValueError("The hourly input model currently requires one-hour steps.")
    start = parse_timestamp(forecast.start_timestamp)
    rng = Random(settings.random_seed + 1000)
    if forecast.historical_prices_csv:
        history = [(parse_timestamp(r["timestamp"]), float(r["price_eur_kwh"]))
                   for r in _read_csv(forecast.historical_prices_csv)]
        price_source = "historical_csv_hourly_mean"
    else:
        history = []
        for day in range(1, forecast.historical_days + 1):
            for hour in range(24):
                timestamp = start - timedelta(days=day) + timedelta(hours=hour)
                price = (forecast.price_base_eur_kwh
                         + forecast.price_amplitude_eur_kwh * sin((hour - 14) * pi / 12)
                         + rng.uniform(-forecast.historical_price_noise_eur_kwh, forecast.historical_price_noise_eur_kwh))
                history.append((timestamp, price))
        price_source = "synthetic_history_hourly_mean"
    if len({timestamp for timestamp, _ in history}) != len(history):
        raise ValueError("Duplicate historical price timestamp.")
    prices = hourly_price_forecast(history, start)
    weather = None if not forecast.weather_csv else _unique_mapping(
        _read_csv(forecast.weather_csv), lambda r: parse_timestamp(r["timestamp"]), "irradiance_w_m2")
    demands = None if not forecast.demand_csv else _unique_mapping(
        _read_csv(forecast.demand_csv),
        lambda r: (parse_timestamp(r["timestamp"]), r["household_id"]), "demand_kwh")
    records = []
    demand_rng = Random(settings.random_seed + 5000)
    daily_factors = {}
    for hour in range(settings.hours):
        # Advance absolute time so DST transitions do not duplicate/miss instants.
        timestamp = (start.astimezone(timezone.utc) + timedelta(hours=hour)).astimezone(start.tzinfo)
        clock_hour = timestamp.hour
        daylight = forecast.sunrise_hour < clock_hour < forecast.sunset_hour
        if weather is None:
            irradiance = (forecast.peak_irradiance_w_m2
                          * sin(pi * (clock_hour - forecast.sunrise_hour)
                                / (forecast.sunset_hour - forecast.sunrise_hour))
                          * rng.uniform(forecast.cloud_factor_min, forecast.cloud_factor_max)) if daylight else 0.0
        else:
            if timestamp not in weather:
                raise ValueError(f"Missing weather for {timestamp.isoformat()}")
            irradiance = weather[timestamp]
            if not daylight and irradiance > 1e-9:
                raise ValueError("Nonzero nighttime irradiance: check timezone/daylight settings.")
        for household in households:
            if demands is None:
                profile = (household.weekend_demand_profile_kwh
                           if timestamp.weekday() >= 5 and household.weekend_demand_profile_kwh is not None
                           else household.demand_profile_kwh)
                key = (household.household_id, timestamp.date())
                if key not in daily_factors:
                    variation = household.daily_variation_fraction
                    daily_factors[key] = demand_rng.uniform(1 - variation, 1 + variation)
                demand = profile[clock_hour] * daily_factors[key]
            else:
                key = (timestamp, household.household_id)
                if key not in demands:
                    raise ValueError(f"Missing demand for {key}")
                demand = demands[key]
            records.append(HourlyInput(
                hour, timestamp.isoformat(), household.household_id, irradiance,
                pv_forecast(household.pv_capacity_kw, irradiance, forecast.performance_factor, 1),
                demand, prices[clock_hour],
                "synthetic_weather_forecast" if weather is None else "weather_csv_forecast",
                ("synthetic_household_profile" if household.building_type == "legacy_house" else "synthetic_building_profile")
                if demands is None else "demand_csv_forecast",
                price_source,
            ))
    return records


def export_inputs(records: list[HourlyInput], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(records[0])))
        writer.writeheader()
        writer.writerows(asdict(record) for record in records)
