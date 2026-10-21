"""Additional result views with exported, inspectable chart data."""

from collections import defaultdict
from pathlib import Path

from src.external_grid import GRID_ACCOUNT
from src.metrics import calculate_metrics
from src.output import write_csv
from src.simulator import SimulationResult


def prepare_chart_data(results: list[SimulationResult]) -> dict[str, list[dict]]:
    data = {name: [] for name in (
        "hourly_profiles", "surplus_destinations", "household_cost_distribution",
        "regulation_effects", "battery_energy_flows", "transaction_prices")}
    metrics = {}
    for result in results:
        metric = metrics[result.name] = calculate_metrics(result)
        for hour in sorted({b.hour for b in result.balances}):
            balances = [b for b in result.balances if b.hour == hour]
            trades = [t for t in result.transactions if t.hour == hour]
            data["hourly_profiles"].append({
                "scenario": result.name, "hour": hour, "timestamp": balances[0].timestamp,
                "pv_kwh": sum(b.pv_kwh for b in balances),
                "demand_kwh": sum(b.demand_kwh for b in balances),
                "p2p_kwh": sum(t.quantity_kwh for t in trades if t.market == "p2p"),
                "grid_imports_kwh": sum(t.quantity_kwh for t in trades if t.market == "grid" and t.seller_id == GRID_ACCOUNT),
            })
        data["surplus_destinations"].append({
            "scenario": result.name, "p2p_kwh": metric["p2p_energy_kwh"],
            "aggregator_kwh": metric["aggregator_energy_kwh"],
            "grid_exports_kwh": metric["grid_exports_kwh"],
            "deferred_charge_kwh": metric["battery_charge_kwh"] if result.battery_strategy == "p2p_priority" else 0.0,
            "offered_surplus_kwh": result.surplus_available_kwh,
        })
        for household_id in sorted({b.household_id for b in result.balances}):
            data["household_cost_distribution"].append({
                "scenario": result.name, "household_id": household_id,
                "net_cost_eur": -result.ledger.balance(household_id),
            })
        data["battery_energy_flows"].append({
            "scenario": result.name, "charge_kwh": metric["battery_charge_kwh"],
            "discharge_kwh": metric["battery_discharge_kwh"], "loss_kwh": metric["battery_loss_kwh"],
            "stored_change_kwh": metric["battery_final_stored_kwh"] - metric["battery_initial_stored_kwh"],
        })
        data["transaction_prices"].extend({
            "scenario": result.name, "transaction_id": t.transaction_id,
            "hour": t.hour, "market": t.market, "quantity_kwh": t.quantity_kwh,
            "price_eur_kwh": t.price_eur_kwh,
        } for t in result.transactions if t.market in {"p2p", "aggregator"})
    for baseline, regulated in (("A", "B"), ("C", "D"), ("E", "F")):
        if baseline not in metrics or regulated not in metrics:
            continue
        base, reg = metrics[baseline], metrics[regulated]
        data["regulation_effects"].append({
            "comparison": f"{regulated} minus {baseline}",
            "p2p_change_kwh": reg["p2p_energy_kwh"] - base["p2p_energy_kwh"],
            "household_cost_change_eur": reg["household_net_cost_eur"] - base["household_net_cost_eur"],
            "community_cost_change_eur": reg["community_including_regulator_net_cost_eur"] - base["community_including_regulator_net_cost_eur"],
        })
    return data


def generate_additional_charts(results: list[SimulationResult], directory: Path, plt, save, colors: dict) -> None:
    """Use the parent renderer's style and PNG/SVG export convention."""
    data = prepare_chart_data(results)
    for name, rows in data.items():
        if rows:
            write_csv(directory / "data" / f"{name}.csv", rows)
    names = [result.name for result in results]
    grouped = defaultdict(list)
    for row in data["hourly_profiles"]:
        grouped[row["scenario"]].append(row)
    reference = grouped[names[0]]
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    hours = [row["hour"] for row in reference]
    axes[0].plot(hours, [r["pv_kwh"] for r in reference], color="#BD7F23", label="PV", marker=".")
    axes[0].plot(hours, [r["demand_kwh"] for r in reference], color="#315A86", label="Demand", linestyle="--")
    axes[0].set(title=f"Community PV and demand (inputs: {names[0]})", ylabel="kWh per one-hour step")
    axes[0].legend(frameon=False)
    for index, name in enumerate(names):
        axes[1].plot(hours, [r["p2p_kwh"] for r in grouped[name]], label=name,
                     color=colors[name], linestyle="--" if index % 2 else "-", marker=".")
    axes[1].set(title="Hourly P2P trading", ylabel="kWh per one-hour step")
    axes[1].legend(frameon=False, ncol=3)
    for axis in axes:
        axis.set(xlabel="Simulation hour", ylim=(0, None))
        axis.set_xticks(sorted({hours[0], hours[-1], *hours[::4]}))
    save(fig, "hourly_profiles")

    fig, axis = plt.subplots(figsize=(12, 5))
    bottoms = [0.0] * len(names)
    for key, label, color in (
        ("p2p_kwh", "P2P", "#315A86"), ("aggregator_kwh", "Aggregator", "#BD7F23"),
        ("grid_exports_kwh", "Grid exports", "#9AA4AD"),
        ("deferred_charge_kwh", "Charging after P2P (E/F)", "#758A35"),
    ):
        values = [row[key] for row in data["surplus_destinations"]]
        axis.bar(names, values, bottom=bottoms, color=color, label=label)
        bottoms = [bottom + value for bottom, value in zip(bottoms, values)]
    axis.set(title="Destinations of the surplus offered to P2P", ylabel="kWh", xlabel="Scenario")
    axis.set_ylim(0, max(bottoms) * 1.3 + .1)
    axis.legend(frameon=False, loc="upper left", ncol=2)
    save(fig, "surplus_destinations")

    fig, axis = plt.subplots(figsize=(11, 5))
    samples = [[row["net_cost_eur"] for row in data["household_cost_distribution"] if row["scenario"] == name] for name in names]
    boxes = axis.boxplot(samples, tick_labels=names, patch_artist=True,
                         medianprops={"color": "#152E45", "linewidth": 1.8},
                         flierprops={"marker": "o", "markersize": 3})
    for box, name in zip(boxes["boxes"], names):
        box.set_facecolor(colors[name])
        box.set_alpha(.55)
    axis.axhline(0, color="#777777", linewidth=.8)
    axis.set(title="Building meter net cost distribution", xlabel="Scenario", ylabel="EUR per building meter (negative = net revenue)")
    axis.text(.01, .98, "Median and quartiles; whiskers at 1.5 x IQR; dots are observations beyond whiskers.",
              transform=axis.transAxes, va="top", fontsize=9)
    axis.margins(y=.2)
    save(fig, "household_cost_distribution")

    if data["regulation_effects"]:
        rows = data["regulation_effects"]
        labels = [row["comparison"] for row in rows]
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        bars = axes[0].bar(labels, [r["p2p_change_kwh"] for r in rows], color="#315A86")
        axes[0].bar_label(bars, fmt="%+.2f", padding=4)
        axes[0].set(title="Regulation: change in P2P volume", ylabel="kWh difference")
        positions = list(range(len(rows)))
        for offset, key, label, color in (
            (-.18, "household_cost_change_eur", "Building meters", "#315A86"),
            (.18, "community_cost_change_eur", "Meters + regulator", "#BD7F23"),
        ):
            bars = axes[1].bar([p + offset for p in positions], [r[key] for r in rows], width=.35, label=label, color=color)
            axes[1].bar_label(bars, fmt="%+.2f", padding=4, fontsize=9)
        axes[1].set(xticks=positions, xticklabels=labels, title="Regulation: change in net cost", ylabel="EUR difference")
        axes[1].legend(frameon=False, fontsize=9)
        for axis in axes:
            axis.axhline(0, color="#555555", linewidth=.8)
            axis.margins(y=.25)
        save(fig, "regulation_effects")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    rows = data["battery_energy_flows"]
    for offset, key, label, color in (
        (-.18, "charge_kwh", "AC charging", "#315A86"),
        (.18, "discharge_kwh", "AC discharging", "#BD7F23"),
    ):
        axes[0].bar([i + offset for i in range(len(names))], [r[key] for r in rows], width=.35, label=label, color=color)
    for offset, key, label, color in (
        (-.18, "loss_kwh", "Conversion losses", "#9AA4AD"),
        (.18, "stored_change_kwh", "Final minus initial storage", "#758A35"),
    ):
        axes[1].bar([i + offset for i in range(len(names))], [r[key] for r in rows], width=.35, label=label, color=color)
    for axis, title in zip(axes, ("Battery charging and discharging", "Battery losses and inventory change")):
        axis.set(xticks=range(len(names)), xticklabels=names, title=title, xlabel="Scenario", ylabel="kWh")
        axis.axhline(0, color="#777777", linewidth=.8)
        axis.legend(frameon=False, fontsize=9)
        axis.margins(y=.25)
    save(fig, "battery_energy_flows")

    columns = min(3, len(names))
    row_count = (len(names) + columns - 1) // columns
    fig, axes = plt.subplots(row_count, columns, figsize=(12, 3.6 * row_count), squeeze=False, sharex=True, sharey=True)
    for axis, name in zip(axes.flat, names):
        for market, marker, color in (("p2p", "o", "#315A86"), ("aggregator", "x", "#BD7F23")):
            points = [r for r in data["transaction_prices"] if r["scenario"] == name and r["market"] == market]
            if points:
                axis.scatter([p["quantity_kwh"] for p in points], [p["price_eur_kwh"] for p in points],
                             marker=marker, color=color, s=20, alpha=.7, label=market)
        if not any(r["scenario"] == name for r in data["transaction_prices"]):
            axis.text(.5, .5, "No internal trades", transform=axis.transAxes, ha="center")
        else:
            axis.legend(frameon=False, fontsize=9)
        axis.set(title=f"Scenario {name}", xlabel="Transaction energy (kWh)", ylabel="Trading price (EUR/kWh)", xlim=(0, None), ylim=(0, None))
    for axis in list(axes.flat)[len(names):]:
        axis.set_visible(False)
    fig.suptitle("Internal transaction prices and quantities (reward excluded)", fontsize=14, fontweight="bold")
    save(fig, "transaction_prices")
