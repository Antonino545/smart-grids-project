"""Paired policy comparisons: underlying load totals and PV remain fixed."""

from src.output import write_csv, write_json
from pathlib import Path
import os
import tempfile


def compare_demand_response(fixed, shifted, directory, charts=True):
    base = {s["scenario"]: s["metrics"] for s in fixed["scenarios"]}
    flex = {s["scenario"]: s["metrics"] for s in shifted["scenarios"]}
    if base.keys() != flex.keys():
        raise ValueError("Demand-response comparisons need the same scenario set.")
    rows = []
    for name in base:
        for key in ("pv_generation_kwh", "demand_kwh"):
            if abs(base[name][key] - flex[name][key]) > 1e-7:
                raise ValueError("Demand shifting changed total PV or total demand.")
        for condition, metrics in (("Fixed demand", base[name]), ("Shifted demand", flex[name])):
            rows.append({"scenario": name, "condition": condition, **metrics})
    write_csv(directory / "demand_response_comparison.csv", rows)
    write_json(directory / "demand_response_comparison.json", {
        "fixed_input_sha256": fixed["input_sha256"], "shifted_input_sha256": shifted["input_sha256"],
        "demand_response": shifted["demand_response"], "rows": rows,
        "note": "Same building properties, PV, daily load totals and market seeds; only eligible load timing changes."})
    if not charts:
        return
    os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "smartgrid-matplotlib"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    panels = [("p2p_energy_kwh", "P2P electricity traded", "kWh"),
              ("pv_direct_self_consumption_kwh", "Direct use of own PV (before batteries)", "kWh"),
              ("grid_imports_kwh", "External-grid imports", "kWh"),
              ("household_net_cost_eur", "Building-meter net cost", "EUR")]
    x = list(range(len(base)))
    for axis, (key, title, unit) in zip(axes.flat, panels):
        for offset, values, label, color in ((-.18, base, "Fixed demand", "#315A86"),
                                              (.18, flex, "Shifted demand", "#BD7F23")):
            axis.bar([v+offset for v in x], [values[n][key] for n in base], width=.35, label=label, color=color)
        axis.set(title=title, ylabel=unit, xticks=x, xticklabels=list(base))
        axis.margins(y=.12)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False)
    fig.text(.02, .02, "Synthetic day-ahead flexibility; only PV prosumers without battery ownership shift. Daily energy is unchanged.", fontsize=9)
    fig.tight_layout(rect=(0,.05,1,.95))
    for extension in ("png", "svg"):
        fig.savefig(directory / "charts" / f"demand_response_comparison.{extension}", dpi=180,
                    metadata={"Date":None} if extension == "svg" else None)
    plt.close(fig)
    import csv
    with (directory / "inputs" / "households.csv").open() as handle:
        eligible = {r["household_id"] for r in csv.DictReader(handle)
                    if r["participant_role"] == "prosumer" and r["has_battery"] == "False"}
    profiles = {}
    for condition, folder in (("fixed", directory), ("shifted", directory / "demand_response")):
        with (folder / "inputs" / "hourly_inputs.csv").open() as handle:
            for row in csv.DictReader(handle):
                if row["household_id"] not in eligible:
                    continue
                hour = int(row["hour"])
                record = profiles.setdefault(hour, {"hour":hour,"pv_kwh":0.,"fixed_demand_kwh":0.,"shifted_demand_kwh":0.})
                record[f"{condition}_demand_kwh"] += float(row["demand_kwh"])
                if condition == "fixed":
                    record["pv_kwh"] += float(row["pv_kwh"])
    data = [profiles[h] for h in sorted(profiles)]
    write_csv(directory / "charts" / "data" / "demand_response_hourly.csv", data)
    fig, axis = plt.subplots(figsize=(12,5))
    for key,label,color,style in (("fixed_demand_kwh","Fixed demand","#4C5A65","-."),
                                  ("shifted_demand_kwh","Shifted demand","#BD7F23","-"),
                                  ("pv_kwh","Own PV forecast","#315A86","--")):
        axis.plot([r["hour"] for r in data],[r[key] for r in data],label=label,color=color,linestyle=style,linewidth=2)
    axis.set(title=f"Load timing of the {len(eligible)} eligible prosumers without batteries", xlabel="Simulation hour",
             ylabel="Aggregate kWh per hourly step", ylim=(0,None))
    hours = [r["hour"] for r in data]
    axis.set_xticks(sorted({hours[0],hours[-1],*hours[::max(1,len(hours)//6)]}))
    axis.legend(frameon=False)
    fig.text(.02,.02,"Equal areas under the two demand curves. Transfers use each owner's surplus, not the aggregate curve; peak and schedule limits apply.",fontsize=9)
    fig.tight_layout(rect=(0,.06,1,1))
    for extension in ("png","svg"):
        fig.savefig(directory / "charts" / f"demand_response_hourly.{extension}",dpi=180,
                    metadata={"Date":None} if extension=="svg" else None)
    plt.close(fig)
