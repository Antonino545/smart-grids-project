from datetime import datetime, timedelta, timezone

import pytest

from config.settings import ForecastSettings, SimulationSettings
from src.forecasting import generate_inputs
from src.households import generate_households
from src.solar import hourly_clear_sky, sun_position

TURIN = dict(latitude_deg=45.07, longitude_deg=7.686, altitude_m=240.0, transmittance=.66, albedo=.2)
CEST = timezone(timedelta(hours=2))


def clear_day(tilt, day=datetime(2026, 6, 15, tzinfo=CEST)):
    return [hourly_clear_sky(day + timedelta(hours=h), TURIN["latitude_deg"], TURIN["longitude_deg"],
                             TURIN["altitude_m"], TURIN["transmittance"], TURIN["albedo"], tilt, 0.0)
            for h in range(24)]


def test_turin_solar_noon_and_night():
    # Highest sun around 13:30 local summer time; nothing before 05:00 or after 22:00.
    noon = min(((sun_position(datetime(2026, 6, 15, 11, m, tzinfo=timezone.utc), 45.07, 7.686)[0], m)
                for m in range(60)))[1]
    assert 25 <= noon <= 33
    day = clear_day(20)
    assert all(plane == 0 for plane, _ in day[:5] + day[22:])
    assert max(range(24), key=lambda h: day[h][0]) == 13


def test_june_clear_sky_matches_pvgis_for_turin():
    # JRC PVGIS 5.2 clear-sky June day, 45.07 N 7.69 E, south: 7946 / 7902 / 7691 Wh/m2 at 10/20/30 deg.
    for tilt, pvgis in ((10, 7946), (20, 7902), (30, 7691)):
        assert sum(plane for plane, _ in clear_day(tilt)) == pytest.approx(pvgis, rel=.02)
        assert max(plane for plane, _ in clear_day(tilt)) == pytest.approx(950, rel=.03)


def test_expected_june_yield_matches_pvgis():
    # PVGIS June: 4.87 kWh per installed kW per day at 20 deg. Mean cloud factor 0.825.
    forecast = ForecastSettings()
    clear = sum(plane for plane, _ in clear_day(20)) / 1000
    mean_cloud = (forecast.cloud_factor_min + forecast.cloud_factor_max) / 2
    assert clear * mean_cloud * forecast.performance_factor == pytest.approx(4.87, rel=.03)


def test_tilt_changes_panel_light_and_buildings_share_one_sky():
    settings = SimulationSettings()
    buildings = generate_households(settings)
    records = generate_inputs(buildings, settings)
    noon = {r.household_id: r.irradiance_w_m2 for r in records if r.hour == 13}
    by_tilt = {}
    for b in buildings:
        by_tilt.setdefault(b.panel_tilt_deg, set()).add(round(noon[b.household_id], 9))
    assert len(by_tilt) == 3 and all(len(values) == 1 for values in by_tilt.values())
    assert all(r.irradiance_w_m2 == 0 and r.pv_kwh == 0 for r in records if r.hour < 5 or r.hour >= 22)


def test_weather_csv_is_horizontal_light_moved_onto_the_panel(tmp_path):
    settings = SimulationSettings(hours=24)
    buildings = generate_households(settings)
    path = tmp_path / "weather.csv"
    rows = ["timestamp,irradiance_w_m2"]
    for h in range(24):
        stamp = datetime(2026, 6, 15, h, tzinfo=CEST)
        _, horizontal = hourly_clear_sky(stamp, 45.07, 7.686, 240.0, .66, .2, 0.0, 0.0)
        rows.append(f"{stamp.isoformat()},{horizontal}")
    path.write_text("\n".join(rows) + "\n")
    measured = generate_inputs(buildings, settings, ForecastSettings(weather_csv=str(path)))
    house = next(b for b in buildings if b.building_type == "small_house")
    noon = next(r for r in measured if r.hour == 13 and r.household_id == house.household_id)
    assert noon.irradiance_w_m2 == pytest.approx(clear_day(20)[13][0], rel=1e-6)
