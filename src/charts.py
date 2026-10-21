"""Reproducible, headless matplotlib charts sourced directly from simulation results."""

import os
from pathlib import Path
import tempfile

import numpy as np

from src.metrics import calculate_metrics
from src.simulator import SimulationResult

COLORS = {"A": "#315A86", "B": "#D48B25", "C": "#7C8792", "D": "#758A35",
          "E": "#4F8791", "F": "#A46483"}


def generate_charts(results: list[SimulationResult], directory: Path) -> None:
    os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "smartgrid-matplotlib"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.titleweight": "bold", "figure.facecolor": "white"})
    directory.mkdir(parents=True, exist_ok=True)
    metrics = [calculate_metrics(result) for result in results]
    names = [result.name for result in results]
    x = np.arange(len(results))
    colors = [COLORS.get(name, "#315A86") for name in names]
    caption = "Identical hourly inputs across scenarios. See summary.json for data sources and seed. A/B: 55 batteries. C/D: none. E/F: P2P priority. B/D/F: regulated."

    def save(fig, filename):
        fig.text(.02, .015, caption, fontsize=8, color="#555555")
        fig.tight_layout(rect=(0, .05, 1, 1))
        fig.savefig(directory / f"{filename}.png", dpi=180)
        fig.savefig(directory / f"{filename}.svg")
        plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    for axis, key, title, unit in (
        (axes[0], "p2p_share_pct", "P2P share of available surplus", "%"),
        (axes[1], "p2p_energy_kwh", "P2P energy traded", "kWh"),
    ):
        values = [m[key] if m[key] is not None else np.nan for m in metrics]
        bars = axis.bar(names, values, color=colors)
        axis.bar_label(bars, fmt="%.2f", padding=3, fontsize=9)
        axis.set(title=title, ylabel=unit, xlabel="Scenario")
        axis.set_ylim(bottom=0, top=max([v for v in values if np.isfinite(v)] or [1]) * 1.2 + .1)
    save(fig, "p2p_comparison")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for offset, key, label, color in (
        (-.18, "grid_imports_kwh", "Grid imports", "#315A86"),
        (.18, "grid_exports_kwh", "Grid exports", "#D48B25"),
    ):
        axes[0].bar(x + offset, [m[key] for m in metrics], width=.35, label=label, color=color)
    axes[0].set(xticks=x, xticklabels=names, ylabel="kWh", xlabel="Scenario", title="External grid energy")
    axes[0].legend(frameon=False)
    axes[0].set_ylim(bottom=0)
    bars = axes[1].bar(names, [m["aggregator_energy_kwh"] for m in metrics], color="#758A35")
    axes[1].bar_label(bars, fmt="%.2f", padding=3, fontsize=9)
    axes[1].set(ylabel="kWh", xlabel="Scenario", title="Aggregator energy (separate scale)")
    axes[1].set_ylim(0, max(m["aggregator_energy_kwh"] for m in metrics) * 1.2 + .1)
    save(fig, "energy_comparison")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for offset, key, label, color in (
        (-.18, "household_net_cost_eur", "Building meters", "#315A86"),
        (.18, "community_including_regulator_net_cost_eur", "Meters + regulator", "#D48B25"),
    ):
        axes[0].bar(x + offset, [m[key] for m in metrics], width=.35, label=label, color=color)
    axes[0].set(xticks=x, xticklabels=names, ylabel="EUR (net payment)", title="Electricity costs by accounting boundary")
    axes[0].axhline(0, color="#777777", linewidth=.8)
    axes[0].legend(frameon=False, fontsize=9)
    for offset, key, label, color in (
        (-.25, "regulator_fee_revenue_eur", "Fees", "#315A86"),
        (0, "regulator_reward_expenditure_eur", "Rewards", "#D48B25"),
        (.25, "regulator_remaining_funds_eur", "Closing fund", "#758A35"),
    ):
        axes[1].bar(x + offset, [m[key] for m in metrics], width=.24, label=label, color=color)
    axes[1].set(xticks=x, xticklabels=names, ylabel="EUR", title="Regulator cash flows")
    axes[1].legend(frameon=False, fontsize=9)
    save(fig, "financial_comparison")

    fig, axis = plt.subplots(figsize=(11, 4.8))
    for result in results:
        if result.regulator:
            history = result.regulator.history
            axis.plot([0] + [h["hour"] + 1 for h in history],
                      [result.regulator.settings.initial_budget_eur] + [h["closing_funds_eur"] for h in history],
                      label=result.name, color=COLORS[result.name], marker=".", linestyle="--" if result.name == "F" else "-")
    maximum_hour = max(b.hour for result in results for b in result.balances) + 1
    axis.set_xticks(sorted({0, maximum_hour, *range(4, maximum_hour, 4)}))
    axis.axhline(1, color="#999999", linewidth=.8, linestyle=":", label="EUR 1 tier")
    axis.axhline(5, color="#555555", linewidth=.8, linestyle=":", label="EUR 5 tier")
    axis.set(xlabel="Elapsed hours (closing balance)", ylabel="EUR", title="Regulator fund evolution", ylim=(0, None))
    axis.legend(frameon=False, ncol=3)
    save(fig, "regulator_budget")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for result, metric in zip(results, metrics):
        if not metric["active_battery_count"]:
            continue
        hours = sorted({b.hour for b in result.balances})
        stored = [metric["battery_initial_stored_kwh"]] + [
            sum(b.stored_end_kwh for b in result.balances if b.hour == hour) for hour in hours]
        axes[0].plot(range(len(stored)), stored, label=result.name, color=COLORS[result.name],
                     linestyle="--" if result.battery_strategy == "p2p_priority" else "-")
    axes[0].set(title="Aggregate battery stored energy", xlabel="Elapsed hours", ylabel="kWh")
    axes[0].legend(frameon=False)
    axes[0].set_ylim(bottom=0)
    maximum_hour = max(b.hour for result in results for b in result.balances) + 1
    axes[0].set_xticks(sorted({0, maximum_hour, *range(4, maximum_hour, 4)}))
    axes[1].bar(x - .18, [m["pv_surplus_before_battery_charging_kwh"] for m in metrics], width=.35,
                color="#315A86", label="PV surplus before charging")
    axes[1].bar(x + .18, [m["surplus_available_after_self_balancing_kwh"] for m in metrics], width=.35,
                color="#D48B25", label="Surplus offered to P2P")
    axes[1].set(xticks=x, xticklabels=names, ylabel="kWh", title="Surplus denominators")
    axes[1].set_ylim(0, max(m["pv_surplus_before_battery_charging_kwh"] for m in metrics) * 1.28 + .1)
    axes[1].legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "battery_and_surplus")

    battery_result = next((r for r in results if any(b.soc is not None for b in r.balances)), None)
    if battery_result:
        owners = sorted({b.household_id for b in battery_result.balances if b.soc is not None})
        hours = sorted({b.hour for b in battery_result.balances})
        lookup = {(b.household_id, b.hour): b.soc for b in battery_result.balances}
        matrix = [[lookup[(owner, hour)] for hour in hours] for owner in owners]
        fig, axis = plt.subplots(figsize=(11, 5))
        image = axis.imshow(matrix, aspect="auto", vmin=0, vmax=1, cmap="cividis", interpolation="nearest")
        axis.set(title=f"Battery SOC after each hour, scenario {battery_result.name}", xlabel="Simulation hour", ylabel="Battery owner")
        ticks = list(range(0, len(owners), max(1, len(owners) // 8)))
        axis.set_yticks(ticks, [owners[i] for i in ticks])
        axis.set_xticks(sorted({0, len(hours) - 1, *range(4, len(hours), 4)}))
        fig.colorbar(image, ax=axis, label="SOC (fraction of nominal capacity)")
        save(fig, "battery_soc")

    from src.result_charts import generate_additional_charts
    generate_additional_charts(results, directory, plt, save, COLORS)
