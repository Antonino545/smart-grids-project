from datetime import datetime, timedelta
from math import isfinite

import pytest

from config.settings import ForecastSettings, SimulationSettings
from src.forecasting import generate_inputs, hourly_price_forecast
from src.households import generate_households


def test_all_hourly_inputs_are_plausible_and_repeatable():
    settings = SimulationSettings()
    households = generate_households(settings)
    capacities = {h.household_id: h.pv_capacity_kw for h in households}
    records = generate_inputs(households, settings)
    assert records == generate_inputs(households, settings)
    assert len(records) == len({(r.hour, r.household_id) for r in records}) == 2400
    assert all(r.pv_kwh == 0 for r in records if r.hour <= 6 or r.hour >= 20)
    assert all(0 <= r.pv_kwh <= capacities[r.household_id] for r in records)
    assert all(r.demand_kwh >= 0 and isfinite(r.reference_price_eur_kwh) for r in records)
    assert all("synthetic" in r.weather_source and "synthetic" in r.price_source for r in records)


def test_price_forecast_never_uses_future_observations():
    cutoff = datetime.fromisoformat("2026-06-15T00:00:00+02:00")
    history = [(cutoff - timedelta(days=1) + timedelta(hours=h), h / 100) for h in range(24)]
    expected = hourly_price_forecast(history, cutoff)
    history += [(cutoff + timedelta(hours=h), 999) for h in range(24)]
    assert hourly_price_forecast(history, cutoff) == expected
    with pytest.raises(ValueError, match="cover every hour"):
        hourly_price_forecast(history[24:], cutoff)


def test_partial_external_data_is_rejected(tmp_path):
    path = tmp_path / "weather.csv"
    path.write_text("timestamp,irradiance_w_m2\n2026-06-15T00:00:00+02:00,0\n")
    settings = SimulationSettings()
    with pytest.raises(ValueError, match="Missing weather"):
        generate_inputs(generate_households(settings), settings, ForecastSettings(weather_csv=str(path)))


def test_real_csv_adapters_and_source_labels(tmp_path):
    import csv
    from dataclasses import asdict
    settings = SimulationSettings(household_count=2, group_count=1, battery_household_count=1)
    households = generate_households(settings)
    reference = generate_inputs(households, settings)
    weather = tmp_path / "weather.csv"
    with weather.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp", "irradiance_w_m2"])
        writer.writerows((r.timestamp, r.irradiance_w_m2) for r in reference if r.household_id == "H001")
    demand = tmp_path / "demand.csv"
    with demand.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp", "household_id", "demand_kwh"])
        writer.writerows((r.timestamp, r.household_id, r.demand_kwh) for r in reference)
    price = tmp_path / "price.csv"
    start = datetime.fromisoformat(reference[0].timestamp)
    with price.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp", "price_eur_kwh"])
        writer.writerows(((start - timedelta(days=1) + timedelta(hours=h)).isoformat(), .123) for h in range(24))
        writer.writerow([start.isoformat(), 999])
    records = generate_inputs(households, settings, ForecastSettings(
        weather_csv=str(weather), demand_csv=str(demand), historical_prices_csv=str(price)))
    assert all(r.reference_price_eur_kwh == .123 for r in records)
    assert [r.pv_kwh for r in records] == [r.pv_kwh for r in reference]
    assert [r.demand_kwh for r in records] == [r.demand_kwh for r in reference]
    assert all("synthetic" not in r.weather_source and "synthetic" not in r.price_source for r in records)
    with price.open("a") as handle:
        handle.write(f"{start.isoformat()},1\n")
    with pytest.raises(ValueError, match="Duplicate historical"):
        generate_inputs(households, settings, ForecastSettings(historical_prices_csv=str(price)))
