"""Actual mean hourly inputs by building type; no observed-data claims."""

from collections import defaultdict
from pathlib import Path

from src.building_profiles import TYPE_LABELS
from src.output import write_csv

TYPE_COLORS = {"small_house": "#315A86", "apartment_block": "#BD7F23",
               "supermarket": "#758A35", "school": "#A46483", "legacy_house": "#315A86"}


def building_chart_data(households, inputs):
    lookup = {h.household_id: h for h in households}
    grouped = defaultdict(list)
    for record in inputs:
        grouped[(lookup[record.household_id].building_type, record.hour)].append(record)
    hourly = [{"building_type": kind, "hour": hour, "timestamp": records[0].timestamp,
               "building_count": len(records),
               "mean_demand_kwh": sum(r.demand_kwh for r in records) / len(records),
               "mean_pv_kwh": sum(r.pv_kwh for r in records) / len(records)}
              for (kind, hour), records in sorted(grouped.items())]
    types = []
    for kind in sorted({h.building_type for h in households}):
        members = [h for h in households if h.building_type == kind]
        types.append({"building_type": kind, "count": len(members),
                      "battery_count": sum(h.has_battery for h in members),
                      "dwelling_units": sum(h.dwelling_units for h in members),
                      "mean_roof_m2": sum(h.roof_area_m2 for h in members) / len(members),
                      "mean_floors": sum(h.floors for h in members) / len(members),
                      "mean_pv_kw": sum(h.pv_capacity_kw for h in members) / len(members),
                      "mean_weekday_demand_kwh": sum(sum(h.demand_profile_kwh) for h in members) / len(members)})
    return hourly, types


def generate_building_charts(households, inputs, directory: Path):
    import matplotlib.pyplot as plt
    hourly, types = building_chart_data(households, inputs)
    write_csv(directory / "data" / "building_type_hourly.csv", hourly)
    write_csv(directory / "data" / "building_type_summary.csv", types)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for index, row in enumerate(types):
        kind = row["building_type"]
        records = [r for r in hourly if r["building_type"] == kind]
        hours = [r["hour"] for r in records]
        for axis, key in zip(axes, ("mean_demand_kwh", "mean_pv_kwh")):
            axis.plot(hours, [r[key] for r in records], color=TYPE_COLORS[kind],
                      label=f'{TYPE_LABELS[kind]} (n={row["count"]})',
                      linestyle=("-", "--", "-.", ":")[index % 4])
            axis.set_xticks(sorted({hours[0], hours[-1], *hours[::max(1,len(hours)//6)]}))
    for axis, title in zip(axes, ("Demand by building type", "PV generation by building type")):
        axis.set(title=title, xlabel="Simulation hour", ylabel="Mean kWh per building per hourly step", ylim=(0,None))
        axis.legend(frameon=False, fontsize=9)
    fig.text(.02,.015,"Synthetic archetypes. Mean per building, not type totals. The same inputs are used in every scenario.",fontsize=9,color="#555555")
    fig.tight_layout(rect=(0,.05,1,1))
    for extension in ("png","svg"):
        fig.savefig(directory / f"building_type_profiles.{extension}",dpi=180,
                    metadata={"Date":None} if extension == "svg" else None)
    plt.close(fig)
