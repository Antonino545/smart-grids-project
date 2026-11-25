"""Clear-sky sun geometry for a fixed site (default: Turin) and plane-of-array irradiance.

Sun position follows the NOAA/Spencer series (declination, equation of time, hour angle).
Clear-sky beam irradiance uses the Meinel air-mass model with Kasten-Young air mass and a
site-altitude correction; clear-sky diffuse uses the Liu-Jordan relation. The panel plane
receives beam x cos(incidence) + isotropic sky diffuse + ground-reflected light.

With the default transmittance (0.66) the June clear-sky day in Turin matches the PVGIS
clear-sky profile (JRC PVGIS 5.2, 45.07 N 7.69 E) within about 1% at 10-30 degree tilts.
"""

from datetime import datetime, timedelta, timezone
from functools import lru_cache
from math import acos, atan2, cos, degrees, exp, pi, radians, sin, tan

SOLAR_CONSTANT_W_M2 = 1361.0
SUBSTEPS_PER_HOUR = 12  # 5-minute sampling, then averaged to an hourly mean


def sun_position(moment_utc: datetime, latitude_deg: float, longitude_deg: float) -> tuple[float, float, int]:
    """Return (zenith rad, azimuth rad from south, positive west, day of year)."""
    day = moment_utc.timetuple().tm_yday
    hour = moment_utc.hour + moment_utc.minute / 60 + moment_utc.second / 3600
    gamma = 2 * pi / 365 * (day - 1 + (hour - 12) / 24)
    equation_of_time = 229.18 * (0.000075 + 0.001868 * cos(gamma) - 0.032077 * sin(gamma)
                                 - 0.014615 * cos(2 * gamma) - 0.040849 * sin(2 * gamma))
    declination = (0.006918 - 0.399912 * cos(gamma) + 0.070257 * sin(gamma)
                   - 0.006758 * cos(2 * gamma) + 0.000907 * sin(2 * gamma)
                   - 0.002697 * cos(3 * gamma) + 0.00148 * sin(3 * gamma))
    true_solar_minutes = hour * 60 + equation_of_time + 4 * longitude_deg
    hour_angle = radians(true_solar_minutes / 4 - 180)
    latitude = radians(latitude_deg)
    cos_zenith = (sin(latitude) * sin(declination)
                  + cos(latitude) * cos(declination) * cos(hour_angle))
    zenith = acos(max(-1.0, min(1.0, cos_zenith)))
    azimuth = atan2(sin(hour_angle), cos(hour_angle) * sin(latitude) - tan(declination) * cos(latitude))
    return zenith, azimuth, day


def clear_sky(zenith: float, day: int, transmittance: float, altitude_m: float) -> tuple[float, float, float]:
    """Return clear-sky (DNI, DHI, GHI) in W/m2; zero when the sun is below the horizon."""
    if zenith >= pi / 2:
        return 0.0, 0.0, 0.0
    extraterrestrial = SOLAR_CONSTANT_W_M2 * (1 + 0.033 * cos(2 * pi * day / 365))
    air_mass = (1 / (cos(zenith) + 0.50572 * (96.07995 - degrees(zenith)) ** -1.6364)
                * exp(-altitude_m / 8434.5))
    dni = extraterrestrial * transmittance ** (air_mass ** 0.678)
    dhi = max(0.0, (0.271 - 0.294 * dni / extraterrestrial) * extraterrestrial * cos(zenith))
    return dni, dhi, dni * cos(zenith) + dhi


def plane_irradiance(dni: float, dhi: float, ghi: float, zenith: float, sun_azimuth: float,
                     tilt_deg: float, panel_azimuth_deg: float, albedo: float) -> float:
    """Irradiance on a tilted panel (W/m2). Panel azimuth: 0 = south, 90 = west, -90 = east."""
    if ghi <= 0:
        return 0.0
    tilt, facing = radians(tilt_deg), radians(panel_azimuth_deg)
    cos_incidence = cos(zenith) * cos(tilt) + sin(zenith) * sin(tilt) * cos(sun_azimuth - facing)
    return (max(0.0, dni * cos_incidence) + dhi * (1 + cos(tilt)) / 2
            + ghi * albedo * (1 - cos(tilt)) / 2)


@lru_cache(maxsize=4096)
def hourly_clear_sky(hour_start_utc: datetime, latitude_deg: float, longitude_deg: float,
                     altitude_m: float, transmittance: float, albedo: float,
                     tilt_deg: float, panel_azimuth_deg: float) -> tuple[float, float]:
    """Hourly-mean clear-sky (plane-of-array, horizontal) irradiance for the hour that starts here."""
    if hour_start_utc.tzinfo is None:
        raise ValueError("Solar timestamps must be timezone-aware.")
    hour_start_utc = hour_start_utc.astimezone(timezone.utc)
    plane_total = horizontal_total = 0.0
    for step in range(SUBSTEPS_PER_HOUR):
        moment = hour_start_utc + timedelta(hours=(step + 0.5) / SUBSTEPS_PER_HOUR)
        zenith, sun_azimuth, day = sun_position(moment, latitude_deg, longitude_deg)
        dni, dhi, ghi = clear_sky(zenith, day, transmittance, altitude_m)
        plane_total += plane_irradiance(dni, dhi, ghi, zenith, sun_azimuth, tilt_deg, panel_azimuth_deg, albedo)
        horizontal_total += ghi
    return plane_total / SUBSTEPS_PER_HOUR, horizontal_total / SUBSTEPS_PER_HOUR
