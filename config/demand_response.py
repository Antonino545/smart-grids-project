"""Illustrative load-flexibility limits, not measured appliance capabilities."""

from dataclasses import dataclass, field
from math import isfinite


@dataclass(frozen=True)
class DemandResponseSettings:
    enabled: bool = False
    max_shift_hours: int = 6
    max_hourly_increase_fraction: float = 0.5
    flexible_fraction_by_type: dict[str, float] = field(default_factory=lambda: {
        "small_house": 0.20, "apartment_block": 0.15, "supermarket": 0.05, "school": 0.10})
    operating_window_by_type: dict[str, list[int]] = field(default_factory=lambda: {
        "small_house": [6, 23], "apartment_block": [6, 23],
        "supermarket": [7, 22], "school": [8, 17]})

    def __post_init__(self):
        if type(self.enabled) is not bool or type(self.max_shift_hours) is not int or not 0 <= self.max_shift_hours <= 23:
            raise ValueError("Demand response requires a boolean switch and shift distance within 0..23 hours.")
        if not isfinite(self.max_hourly_increase_fraction) or self.max_hourly_increase_fraction < 0:
            raise ValueError("Hourly load increase must be finite and nonnegative.")
        kinds = {"small_house", "apartment_block", "supermarket", "school"}
        if set(self.flexible_fraction_by_type) != kinds or set(self.operating_window_by_type) != kinds:
            raise ValueError("Demand-response settings must cover all four building types.")
        for fraction in self.flexible_fraction_by_type.values():
            if not isfinite(fraction) or not 0 <= fraction <= 1:
                raise ValueError("Flexible load fractions must lie in [0,1].")
        for window in self.operating_window_by_type.values():
            if not isinstance(window, (list, tuple)) or len(window) != 2 or any(type(h) is not int for h in window):
                raise ValueError("Operating windows must contain two integer hours.")
            if not 0 <= window[0] < window[1] <= 24:
                raise ValueError("Operating windows must be ordered within one day.")
