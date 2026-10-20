"""PV self-consumption followed by eligible owner-only battery operation."""

from dataclasses import asdict, dataclass

from src.battery import BatteryState
from src.forecasting import HourlyInput


@dataclass
class BalanceResult:
    hour: int
    timestamp: str
    household_id: str
    pv_kwh: float
    demand_kwh: float
    self_consumption_kwh: float
    pv_surplus_before_charging_kwh: float
    charge_kwh: float
    discharge_kwh: float
    battery_loss_kwh: float
    stored_start_kwh: float
    stored_end_kwh: float
    soc: float | None
    balance_kwh: float

    def as_dict(self) -> dict:
        return asdict(self)

    def verify(self, tolerance: float = 1e-8) -> None:
        ac_error = self.pv_kwh + self.discharge_kwh - self.demand_kwh - self.charge_kwh - self.balance_kwh
        storage_error = (self.stored_end_kwh - self.stored_start_kwh
                         - self.charge_kwh + self.discharge_kwh + self.battery_loss_kwh)
        if abs(ac_error) > tolerance or abs(storage_error) > tolerance:
            raise ValueError("Self-balancing energy conservation failed.")
        if self.charge_kwh > tolerance and self.discharge_kwh > tolerance:
            raise ValueError("Simultaneous charging and discharging is forbidden.")


def self_balance(record: HourlyInput, battery: BatteryState | None,
                 timestep_hours: float = 1.0, defer_surplus_charging: bool = False) -> BalanceResult:
    from src.battery import BatteryFlow
    initial = battery.stored_kwh if battery else 0.0
    raw_balance = record.pv_kwh - record.demand_kwh
    flow = BatteryFlow()
    if battery and not (defer_surplus_charging and raw_balance > 0):
        flow = battery.operate(raw_balance, timestep_hours)
    result = BalanceResult(
        record.hour, record.timestamp, record.household_id, record.pv_kwh, record.demand_kwh,
        min(record.pv_kwh, record.demand_kwh), max(0.0, raw_balance),
        flow.charge_kwh, flow.discharge_kwh, flow.loss_kwh, initial,
        battery.stored_kwh if battery else 0.0, battery.soc if battery else None,
        raw_balance - flow.charge_kwh + flow.discharge_kwh,
    )
    result.verify()
    return result
