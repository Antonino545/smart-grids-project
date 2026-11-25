"""Building archetypes for a Turin (Torino) neighbourhood.

Sources behind the defaults (see docs/building_model.md for detail):
- PV yield and panel tilt: JRC PVGIS 5.2 for 45.07 N, 7.69 E (optimum fixed tilt 40 deg south;
  June yield is highest at 10-15 deg). Tiled roofs in northern Italy are pitched at 35-45 %
  (about 19-24 deg), so house panels lie flush at 20 deg.
- Home size: ISTAT 2023, occupied homes in Italian cities average 93.5 m2.
- Home electricity: ARERA reference 2,200-2,700 kWh/year (2-3 people); Piedmont households
  average 2.1 people.
Roof ranges, panel coverage and PV limits are chosen so roof x coverage x density never
exceeds the limit with the default 0.20 kW/m2 modules: the limit is a cap, not the usual size.
"""

from dataclasses import dataclass, field, replace
from math import isfinite


@dataclass(frozen=True)
class BuildingTypeSettings:
    share: float
    roof_min_m2: float
    roof_max_m2: float
    floors_min: int
    floors_max: int
    home_area_m2_min: float = 70.0
    home_area_m2_max: float = 110.0
    daily_energy_min: float = 7.0
    daily_energy_max: float = 12.0
    energy_basis: str = "per_home"
    profile: str = "residential"
    opening_hour: int = 7
    closing_hour: int = 22
    base_load_weight: float = 0.25
    operating_load_weight: float = 1.0
    weekend_multiplier: float = 1.05
    weekend_open: bool = True
    roof_usable_fraction_min: float = 0.22
    roof_usable_fraction_max: float = 0.35
    pv_limit_kw: float = 10.0
    panel_tilt_deg: float = 20.0
    panel_azimuth_deg: float = 0.0
    battery_scale: float = 1.0
    daily_variation_fraction: float = 0.08

    def __post_init__(self) -> None:
        for name in ("share", "roof_min_m2", "roof_max_m2", "daily_energy_min", "daily_energy_max",
                     "base_load_weight", "operating_load_weight", "weekend_multiplier",
                     "roof_usable_fraction_min", "roof_usable_fraction_max", "pv_limit_kw",
                     "battery_scale", "daily_variation_fraction", "home_area_m2_min", "home_area_m2_max",
                     "panel_tilt_deg"):
            value = getattr(self, name)
            if not isfinite(value) or value < 0:
                raise ValueError(f"Invalid building parameter: {name}")
        for lower, upper in ((self.roof_min_m2, self.roof_max_m2),
                             (self.daily_energy_min, self.daily_energy_max),
                             (self.home_area_m2_min, self.home_area_m2_max)):
            if not 0 < lower <= upper:
                raise ValueError("Building roof/energy/home-size ranges must be positive and ordered.")
        if (type(self.floors_min) is not int or type(self.floors_max) is not int
                or not 1 <= self.floors_min <= self.floors_max):
            raise ValueError("Building floor counts must be positive ordered integers.")
        if not 0 <= self.panel_tilt_deg <= 90 or not -180 <= self.panel_azimuth_deg <= 180:
            raise ValueError("Panel tilt must be 0-90 deg and azimuth -180..180 deg (0 = south).")
        if not 0 < self.roof_usable_fraction_min <= self.roof_usable_fraction_max <= 1:
            raise ValueError("Usable roof fractions must be in (0, 1].")
        if self.energy_basis not in {"per_home", "per_floor_area"}:
            raise ValueError("Unknown building energy basis.")
        if self.profile not in {"residential", "commercial", "school"}:
            raise ValueError("Unknown building profile.")
        if not (type(self.opening_hour) is int and type(self.closing_hour) is int
                and 0 <= self.opening_hour < self.closing_hour <= 24):
            raise ValueError("Opening/closing hours must be ordered hours within a day.")
        if self.base_load_weight <= 0 or self.battery_scale <= 0 or self.pv_limit_kw <= 0:
            raise ValueError("Building base load, battery scale and PV limit must be positive.")
        if self.daily_variation_fraction >= 1 or type(self.weekend_open) is not bool:
            raise ValueError("Daily variation must be below one and weekend_open must be boolean.")


def default_types() -> dict[str, BuildingTypeSettings]:
    return {
        # Detached house (villetta): one home, panels flush on the south pitch of a tiled roof.
        # 80-140 m2 x 16-21 % coverage x 0.20 kW/m2 = 2.6-5.9 kW, mean about 4 kW: typical Italian
        # residential systems are 3-6 kW, sized to the usual 3-6 kW household supply contract.
        "small_house": BuildingTypeSettings(
            .56, 80, 140, 1, 2, daily_energy_min=7, daily_energy_max=12,
            roof_usable_fraction_min=.16, roof_usable_fraction_max=.21, pv_limit_kw=6,
            panel_tilt_deg=20),
        # Condominium: flat roof with lift room and vents; panels on 15 deg racks in rows.
        # 250-500 m2 x 30-45 % x 0.20 = 15-45 kW. Homes per floor = 80 % of footprint / home size.
        "apartment_block": BuildingTypeSettings(
            .30, 250, 500, 4, 8, home_area_m2_min=70, home_area_m2_max=110,
            daily_energy_min=5, daily_energy_max=8, roof_usable_fraction_min=.30,
            roof_usable_fraction_max=.45, pv_limit_kw=50, panel_tilt_deg=15, battery_scale=4),
        # Neighbourhood supermarket: large flat roof, low 10 deg racks for dense coverage.
        # 800-1600 m2 x 40-55 % x 0.20 = 64-176 kW. Load 0.8-1.3 kWh/m2/day (~290-475 kWh/m2/yr).
        "supermarket": BuildingTypeSettings(
            .10, 800, 1600, 1, 1, daily_energy_min=.8, daily_energy_max=1.3,
            energy_basis="per_floor_area", profile="commercial", base_load_weight=.45,
            roof_usable_fraction_min=.40, roof_usable_fraction_max=.55, pv_limit_kw=200,
            panel_tilt_deg=10, battery_scale=10, weekend_multiplier=.9),
        # School: flat roof, 15 deg racks. 700-1600 m2 x 30-45 % x 0.20 = 42-144 kW.
        "school": BuildingTypeSettings(
            .04, 700, 1600, 2, 4, daily_energy_min=.08, daily_energy_max=.15,
            energy_basis="per_floor_area", profile="school", opening_hour=8, closing_hour=17,
            base_load_weight=.08, roof_usable_fraction_min=.30, roof_usable_fraction_max=.45,
            pv_limit_kw=150, panel_tilt_deg=15, battery_scale=6,
            weekend_multiplier=.15, weekend_open=False),
    }


@dataclass(frozen=True)
class BuildingSettings:
    enabled: bool = True
    consumer_count: int = 0
    pv_density_kw_m2: float = 0.20
    types: dict[str, BuildingTypeSettings] = field(default_factory=default_types)

    def __post_init__(self) -> None:
        if type(self.consumer_count) is not int or self.consumer_count < 0:
            raise ValueError("Consumer count must be a nonnegative integer.")
        if not self.enabled and self.consumer_count:
            raise ValueError("Consumer additions require the mixed-building model.")
        if type(self.enabled) is not bool or not isfinite(self.pv_density_kw_m2) or self.pv_density_kw_m2 <= 0:
            raise ValueError("Invalid building model switch or PV density.")
        if set(self.types) != set(default_types()):
            raise ValueError("Configure the four supported building types.")
        if not all(isinstance(spec, BuildingTypeSettings) for spec in self.types.values()):
            raise ValueError("Building types must contain BuildingTypeSettings objects.")
        if abs(sum(spec.share for spec in self.types.values()) - 1) > 1e-9:
            raise ValueError("Building type shares must sum to one.")


def load_building_settings(raw: dict) -> BuildingSettings:
    """Partial type overrides retain other defaults and reject misspelled type/field names."""
    raw = dict(raw)
    defaults = default_types()
    overrides = raw.pop("types", {})
    if not isinstance(overrides, dict) or set(overrides) - set(defaults):
        raise ValueError("Unknown building type override.")
    for name, values in overrides.items():
        if not isinstance(values, dict):
            raise ValueError("Building type overrides must be JSON objects.")
        defaults[name] = replace(defaults[name], **values)
    return BuildingSettings(types=defaults, **raw)
