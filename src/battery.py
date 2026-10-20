"""Battery state with AC-side energy flows and explicit conversion losses."""

from dataclasses import dataclass
from math import isfinite

from config.settings import BatterySettings


@dataclass(frozen=True)
class BatteryFlow:
    charge_kwh: float = 0.0  # PV energy entering the inverter (AC side)
    discharge_kwh: float = 0.0  # Energy delivered to household demand (AC side)
    loss_kwh: float = 0.0


@dataclass
class BatteryState:
    specifications: BatterySettings
    stored_kwh: float

    @classmethod
    def initialize(cls, specifications: BatterySettings) -> "BatteryState":
        return cls(specifications, specifications.capacity_kwh * specifications.initial_soc)

    @property
    def soc(self) -> float:
        return self.stored_kwh / self.specifications.capacity_kwh

    def operate(self, balance_kwh: float, timestep_hours: float = 1.0) -> BatteryFlow:
        if not isfinite(balance_kwh) or not isfinite(timestep_hours) or timestep_hours <= 0:
            raise ValueError("Battery balance/time step must be finite and time step positive.")
        s = self.specifications
        if not s.min_soc - 1e-10 <= self.soc <= s.max_soc + 1e-10:
            raise ValueError("Battery state is outside SOC bounds.")
        if balance_kwh > 0:
            charge = min(balance_kwh, s.max_charge_power_kw * timestep_hours,
                         max(0.0, s.capacity_kwh * s.max_soc - self.stored_kwh) / s.charge_efficiency)
            self.stored_kwh += charge * s.charge_efficiency
            return BatteryFlow(charge_kwh=charge, loss_kwh=charge * (1 - s.charge_efficiency))
        discharge = min(-balance_kwh, s.max_discharge_power_kw * timestep_hours,
                        max(0.0, self.stored_kwh - s.capacity_kwh * s.min_soc) * s.discharge_efficiency)
        self.stored_kwh -= discharge / s.discharge_efficiency
        return BatteryFlow(discharge_kwh=discharge, loss_kwh=discharge * (1 / s.discharge_efficiency - 1))
