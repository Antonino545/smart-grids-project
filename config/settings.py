"""Proposed engineering defaults; no simulation runs when this module is imported."""

from dataclasses import dataclass, field
from random import Random
from math import isfinite


@dataclass(frozen=True)
class BatterySettings:
    """Suggested battery specifications, not fixed professor requirements."""

    capacity_kwh: float = 10.0
    max_charge_power_kw: float = 3.0
    max_discharge_power_kw: float = 3.0
    charge_efficiency: float = 0.95
    discharge_efficiency: float = 0.95
    initial_soc: float = 0.20
    min_soc: float = 0.10
    max_soc: float = 0.90
    strategy: str = "self_consumption_first"

    def __post_init__(self) -> None:
        numeric = (self.capacity_kwh, self.max_charge_power_kw, self.max_discharge_power_kw,
                   self.charge_efficiency, self.discharge_efficiency, self.initial_soc, self.min_soc, self.max_soc)
        if not all(isfinite(value) for value in numeric):
            raise ValueError("Battery parameters must be finite.")
        if not self.capacity_kwh > 0:
            raise ValueError("Battery capacity must be positive.")
        if not (self.max_charge_power_kw > 0 and self.max_discharge_power_kw > 0):
            raise ValueError("Battery power limits must be positive.")
        if not (0 < self.charge_efficiency <= 1 and 0 < self.discharge_efficiency <= 1):
            raise ValueError("Battery efficiencies must be in (0, 1].")
        if not (0 <= self.min_soc <= self.initial_soc <= self.max_soc <= 1):
            raise ValueError("SOC must satisfy 0 <= minimum <= initial <= maximum <= 1.")
        if self.strategy not in {"self_consumption_first", "p2p_priority"}:
            raise ValueError("Battery strategy must be self_consumption_first or p2p_priority.")


@dataclass(frozen=True)
class SimulationSettings:
    """Shared experiment configuration; money in EUR, energy in kWh, power in kW."""

    household_count: int = 100
    group_count: int = 10
    battery_household_count: int = 55
    hours: int = 24
    timestep_hours: float = 1.0
    random_seed: int = 42
    log_level: str = "INFO"
    battery: BatterySettings = field(default_factory=BatterySettings)

    def __post_init__(self) -> None:
        integer_fields = (
            self.household_count, self.group_count, self.battery_household_count,
            self.hours, self.random_seed,
        )
        if any(type(value) is not int for value in integer_fields):
            raise ValueError("Community counts, hours and random seed must be integers.")
        if self.household_count <= 0 or self.group_count <= 0:
            raise ValueError("Household and group counts must be positive.")
        if self.household_count % self.group_count:
            raise ValueError("Households must divide evenly into neighborhood groups.")
        if not 0 <= self.battery_household_count <= self.household_count:
            raise ValueError("Battery household count must be between zero and household count.")
        if self.hours <= 0 or not isfinite(self.timestep_hours) or not self.timestep_hours > 0:
            raise ValueError("Simulation duration and time step must be positive.")
        if self.log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("Unsupported logging level.")

    @property
    def households_per_group(self) -> int:
        return self.household_count // self.group_count

    def create_random_generator(self) -> Random:
        """Return a fresh local generator without changing global random state."""
        return Random(self.random_seed)


@dataclass(frozen=True)
class HouseholdSettings:
    pv_capacity_min_kw: float = 2.0
    pv_capacity_max_kw: float = 8.0
    daily_demand_min_kwh: float = 8.0
    daily_demand_max_kwh: float = 24.0
    bid_multiplier_min: float = 0.70
    bid_multiplier_max: float = 1.15
    ask_multiplier_min: float = 0.90
    ask_multiplier_max: float = 1.35
    base_demand_weight: float = 0.25
    morning_peak_weight: float = 0.65
    morning_peak_hour: float = 7.0
    morning_peak_width_hours: float = 2.0
    evening_peak_weight: float = 1.1
    evening_peak_hour: float = 19.0
    evening_peak_width_hours: float = 3.0
    profile_shift_max_hours: float = 1.0
    profile_noise_fraction: float = 0.25

    def __post_init__(self) -> None:
        from math import isfinite
        numeric = [getattr(self, name) for name in self.__dataclass_fields__]
        if not all(isfinite(value) and value >= 0 for value in numeric):
            raise ValueError("Household parameters must be finite and nonnegative.")
        if (self.base_demand_weight <= 0 or self.morning_peak_width_hours <= 0
                or self.evening_peak_width_hours <= 0 or self.profile_noise_fraction >= 1):
            raise ValueError("Demand baseline/peak widths must be positive and noise less than one.")
        if max(self.morning_peak_hour, self.evening_peak_hour) >= 24:
            raise ValueError("Peak hours must be in [0, 24).")
        for lower, upper in (
            (self.pv_capacity_min_kw, self.pv_capacity_max_kw),
            (self.daily_demand_min_kwh, self.daily_demand_max_kwh),
            (self.bid_multiplier_min, self.bid_multiplier_max),
            (self.ask_multiplier_min, self.ask_multiplier_max),
        ):
            if not (isfinite(lower) and isfinite(upper) and 0 < lower <= upper):
                raise ValueError("Household parameter ranges must be finite, positive and ordered.")


@dataclass(frozen=True)
class ForecastSettings:
    start_timestamp: str = "2026-06-15T00:00:00+02:00"
    sunrise_hour: float = 6.0
    sunset_hour: float = 20.0
    peak_irradiance_w_m2: float = 900.0
    performance_factor: float = 0.85
    historical_days: int = 14
    cloud_factor_min: float = 0.65
    cloud_factor_max: float = 1.0
    historical_price_noise_eur_kwh: float = 0.01
    price_base_eur_kwh: float = 0.17
    price_amplitude_eur_kwh: float = 0.045
    weather_csv: str | None = None
    demand_csv: str | None = None
    historical_prices_csv: str | None = None

    def __post_init__(self) -> None:
        from datetime import datetime
        from math import isfinite
        numeric = (self.sunrise_hour, self.sunset_hour, self.peak_irradiance_w_m2,
                   self.performance_factor, self.cloud_factor_min, self.cloud_factor_max,
                   self.historical_price_noise_eur_kwh)
        if not all(isfinite(value) for value in numeric):
            raise ValueError("Forecast parameters must be finite.")
        if not 0 <= self.cloud_factor_min <= self.cloud_factor_max <= 1 or self.historical_price_noise_eur_kwh < 0:
            raise ValueError("Invalid cloud factors or price noise.")
        start = datetime.fromisoformat(self.start_timestamp)
        if start.tzinfo is None or start.minute or start.second or start.microsecond:
            raise ValueError("Start must be timezone-aware and aligned to an hour.")
        if not 0 <= self.sunrise_hour < self.sunset_hour <= 24:
            raise ValueError("Invalid daylight hours.")
        if not 0 < self.performance_factor <= 1:
            raise ValueError("PV performance factor must be in (0, 1].")
        if not 0 < self.peak_irradiance_w_m2 <= 1000:
            raise ValueError("Synthetic irradiance peak must be in (0, 1000].")
        if type(self.historical_days) is not int or self.historical_days < 1:
            raise ValueError("At least one historical day is required.")
        if not all(isfinite(x) for x in (self.price_base_eur_kwh, self.price_amplitude_eur_kwh)):
            raise ValueError("Prices must be finite.")


@dataclass(frozen=True)
class MarketSettings:
    grid_import_tariff_eur_kwh: float = 0.30
    grid_export_tariff_eur_kwh: float = 0.06
    minimum_offer_eur_kwh: float = 0.06
    maximum_offer_eur_kwh: float = 0.30

    def __post_init__(self) -> None:
        from math import isfinite
        values = (self.grid_import_tariff_eur_kwh, self.grid_export_tariff_eur_kwh,
                  self.minimum_offer_eur_kwh, self.maximum_offer_eur_kwh)
        if not all(isfinite(value) and value >= 0 for value in values):
            raise ValueError("Tariffs and offer limits must be finite and nonnegative.")
        if not (self.grid_export_tariff_eur_kwh <= self.minimum_offer_eur_kwh
                <= self.maximum_offer_eur_kwh <= self.grid_import_tariff_eur_kwh):
            raise ValueError("Offer bounds must lie between grid export and import tariffs.")


@dataclass(frozen=True)
class RegulatorSettings:
    initial_budget_eur: float = 0.0
    grid_fee_eur_kwh: float = 0.01
    lower_tier_budget_eur: float = 1.0
    upper_tier_budget_eur: float = 5.0
    lower_reward_eur_kwh: float = 0.01
    upper_reward_eur_kwh: float = 0.02
    reward_discount_fraction: float = 0.50
    guidance_strength: float = 0.65
    guided_bid_multiplier: float = 1.04
    guided_ask_multiplier: float = 0.96

    def __post_init__(self) -> None:
        from dataclasses import fields
        from math import isfinite
        if not all(isfinite(getattr(self, f.name)) and getattr(self, f.name) >= 0 for f in fields(self)):
            raise ValueError("Regulator parameters must be finite and nonnegative.")
        if not 0 < self.lower_tier_budget_eur < self.upper_tier_budget_eur:
            raise ValueError("Reward budget thresholds must be positive and ordered.")
        if not self.lower_reward_eur_kwh <= self.upper_reward_eur_kwh:
            raise ValueError("Reward rates must be ordered.")
        if not 0 <= self.guidance_strength <= 1 or not 0 <= self.reward_discount_fraction <= 1:
            raise ValueError("Guidance and discount fractions must be in [0, 1].")


@dataclass(frozen=True)
class BlockchainSettings:
    miner_count: int = 10
    hash_prefix: str = "000"
    max_nonce_attempts: int = 5_000_000

    def __post_init__(self) -> None:
        if type(self.miner_count) is not int or self.miner_count < 1:
            raise ValueError("At least one simulated miner is required.")
        if not self.hash_prefix or any(c not in "0123456789abcdef" for c in self.hash_prefix):
            raise ValueError("Hash prefix must be nonempty lowercase hexadecimal.")
        if len(self.hash_prefix) > 6:
            raise ValueError("This teaching simulator limits proof-of-work difficulty to six hex digits.")
        if type(self.max_nonce_attempts) is not int or self.max_nonce_attempts < 1:
            raise ValueError("Mining attempt limit must be a positive integer.")
