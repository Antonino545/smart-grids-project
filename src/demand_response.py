"""Day-ahead redistribution of flexible load into the owner's forecast PV surplus."""

from collections import defaultdict
from dataclasses import replace
from datetime import datetime

from config.demand_response import DemandResponseSettings
from config.buildings import BuildingSettings


def shift_demand(households, inputs, settings: DemandResponseSettings, buildings=None):
    """Return new forecast rows and an auditable transfer journal; never mutate inputs.

    Only PV prosumers without battery ownership participate, including in C/D.
    Transfers stay within a complete local calendar day and the operating window.
    This is a deterministic forecast heuristic, not an appliance scheduling model.
    """
    if not settings.enabled:
        return list(inputs), []
    buildings = buildings or BuildingSettings()
    lookup = {h.household_id: h for h in households}
    grouped = defaultdict(list)
    for index, row in enumerate(inputs):
        grouped[(row.household_id, datetime.fromisoformat(row.timestamp).date())].append(index)
    adjusted = list(inputs)
    journal = []
    for (meter, _), indices in sorted(grouped.items()):
        h = lookup[meter]
        if h.participant_role != "prosumer" or h.has_battery or h.pv_capacity_kw <= 0:
            continue
        if h.building_type not in settings.flexible_fraction_by_type:
            continue  # Legacy model has no calibrated flexibility defaults.
        rows = [inputs[i] for i in indices]
        clock = {i: datetime.fromisoformat(inputs[i].timestamp).hour for i in indices}
        if len(rows) != 24 or set(clock.values()) != set(range(24)):
            continue  # No borrowing from absent hours or the next day.
        opening, closing = settings.operating_window_by_type[h.building_type]
        spec = buildings.types[h.building_type]
        if spec.profile != "residential":
            if datetime.fromisoformat(rows[0].timestamp).weekday() >= 5 and not spec.weekend_open:
                continue
            opening, closing = max(opening, spec.opening_hour), min(closing, spec.closing_hour)
        eligible = [i for i in indices if opening <= clock[i] < closing]
        fraction = settings.flexible_fraction_by_type[h.building_type]
        removed = defaultdict(float)
        added = defaultdict(float)
        # High-deficit hours first; ties use clock hour, independent of input order.
        sources = sorted(eligible, key=lambda i: (-(inputs[i].demand_kwh-inputs[i].pv_kwh), clock[i]))
        for source in sources:
            baseline = inputs[source]
            available = min(fraction * baseline.demand_kwh,
                            max(0.0, baseline.demand_kwh - baseline.pv_kwh))
            targets = sorted((i for i in eligible if i != source
                              and abs(clock[i]-clock[source]) <= settings.max_shift_hours),
                             key=lambda i: (-(inputs[i].pv_kwh-inputs[i].demand_kwh-added[i]), clock[i]))
            for target in targets:
                original = inputs[target]
                headroom = min(max(0.0, original.pv_kwh-original.demand_kwh-added[target]),
                               max(0.0, original.demand_kwh*settings.max_hourly_increase_fraction-added[target]))
                quantity = min(available, headroom)
                if quantity <= 1e-12:
                    continue
                removed[source] += quantity
                added[target] += quantity
                available -= quantity
                journal.append({"household_id": meter, "building_type": h.building_type,
                                "source_hour": baseline.hour, "target_hour": original.hour,
                                "source_timestamp": baseline.timestamp, "target_timestamp": original.timestamp,
                                "quantity_kwh": quantity})
        for i in indices:
            demand = inputs[i].demand_kwh - removed[i] + added[i]
            if removed[i] or added[i]:
                adjusted[i] = replace(inputs[i], demand_kwh=demand,
                                      demand_source=inputs[i].demand_source+"_demand_shifted")
    return adjusted, journal
