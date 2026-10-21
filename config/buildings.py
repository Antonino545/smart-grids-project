"""Illustrative building archetypes, not measured or professor-mandated values."""

from dataclasses import dataclass, field, replace
from math import isfinite


@dataclass(frozen=True)
class BuildingTypeSettings:
    share: float
    roof_min_m2: float
    roof_max_m2: float
    floors_min: int
    floors_max: int
    units_per_floor_min: int = 1
    units_per_floor_max: int = 1
    daily_energy_min: float = 8.0
    daily_energy_max: float = 24.0
    energy_basis: str = "per_dwelling"
    profile: str = "residential"
    opening_hour: int = 7
    closing_hour: int = 22
    base_load_weight: float = 0.25
    operating_load_weight: float = 1.0
    weekend_multiplier: float = 1.05
    weekend_open: bool = True
    roof_usable_fraction_min: float = 0.35
    roof_usable_fraction_max: float = 0.65
    pv_limit_kw: float = 12.0
    battery_scale: float = 1.0
    daily_variation_fraction: float = 0.08

    def __post_init__(self) -> None:
        for name in ("share", "roof_min_m2", "roof_max_m2", "daily_energy_min", "daily_energy_max",
                     "base_load_weight", "operating_load_weight", "weekend_multiplier",
                     "roof_usable_fraction_min", "roof_usable_fraction_max", "pv_limit_kw",
                     "battery_scale", "daily_variation_fraction"):
            value = getattr(self, name)
            if not isfinite(value) or value < 0:
                raise ValueError(f"Invalid building parameter: {name}")
        for lower, upper in ((self.roof_min_m2, self.roof_max_m2),
                             (self.daily_energy_min, self.daily_energy_max)):
            if not 0 < lower <= upper:
                raise ValueError("Building roof/energy ranges must be positive and ordered.")
        for lower, upper in ((self.floors_min, self.floors_max),
                             (self.units_per_floor_min, self.units_per_floor_max)):
            if type(lower) is not int or type(upper) is not int or not 1 <= lower <= upper:
                raise ValueError("Building floor/unit counts must be positive ordered integers.")
        if not 0 < self.roof_usable_fraction_min <= self.roof_usable_fraction_max <= 1:
            raise ValueError("Usable roof fractions must be in (0, 1].")
        if self.energy_basis not in {"per_dwelling", "per_floor_area"}:
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
        "small_house": BuildingTypeSettings(.50, 70, 150, 1, 2),
        "apartment_block": BuildingTypeSettings(
            .30, 180, 360, 4, 10, units_per_floor_min=2, units_per_floor_max=4,
            daily_energy_min=8, daily_energy_max=20, pv_limit_kw=100, battery_scale=4),
        "supermarket": BuildingTypeSettings(
            .10, 600, 1400, 1, 1, daily_energy_min=.5, daily_energy_max=1.1,
            energy_basis="per_floor_area", profile="commercial", base_load_weight=.45,
            pv_limit_kw=300, battery_scale=10, weekend_multiplier=.9),
        "school": BuildingTypeSettings(
            .10, 700, 1600, 2, 3, daily_energy_min=.08, daily_energy_max=.18,
            energy_basis="per_floor_area", profile="school", opening_hour=8, closing_hour=17,
            base_load_weight=.08, pv_limit_kw=300, battery_scale=6,
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
