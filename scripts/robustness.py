"""Multi-seed robustness check: rerun selected scenarios on several seeded communities.

For every seed, all scenarios share one community and one hourly input set (checked by
run_experiments through the input hash). Each seed is run with fixed demand and with
PV-aware demand response. Only aggregated tables and one chart are kept.
"""

import argparse
import json
import sys
import tempfile
from dataclasses import replace
from pathlib import Path
from statistics import mean, stdev

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from main import load_configuration  # noqa: E402
from src.output import write_csv, write_json  # noqa: E402
from src.experiments import run_experiments  # noqa: E402

SCENARIOS = ["A", "B", "D", "F", "K", "L"]
CONDITIONS = {"fixed": False, "demand_response": True}
# KPI name -> True when a higher value is better.
KPIS = {
    "p2p_energy_kwh": True,
    "p2p_share_of_pv_pct": True,
    "grid_imports_kwh": False,
    "grid_exports_kwh": False,
    "household_net_cost_eur": False,
    "community_including_regulator_net_cost_eur": False,
    "community_cost_storage_adjusted_eur": False,
}
TOLERANCE = 1e-6


def storage_value_eur_kwh(config: dict) -> float:
    """Value of one extra kWh left in storage: the import it avoids later, after discharge losses."""
    return config["market"].grid_import_tariff_eur_kwh * config["simulation"].battery.discharge_efficiency


def run_seed(config: dict, seed: int, demand_response: bool, workdir: Path) -> tuple[list[dict], str]:
    seeded = {**config,
              "simulation": replace(config["simulation"], random_seed=seed),
              "demand_response": replace(config["demand_response"], enabled=demand_response)}
    comparison = run_experiments(seeded, workdir, SCENARIOS, charts=False)
    value = storage_value_eur_kwh(config)
    rows = []
    for summary in comparison["scenarios"]:
        m = summary["metrics"]
        if not m["blockchain_valid"] or m["block_count"] != config["simulation"].hours:
            raise ValueError(f"Blockchain check failed: seed {seed}, scenario {summary['scenario']}.")
        if m["regulator_remaining_funds_eur"] < -TOLERANCE:
            raise ValueError(f"Regulator fund went negative: seed {seed}, scenario {summary['scenario']}.")
        stored_change = m["battery_final_stored_kwh"] - m["battery_initial_stored_kwh"]
        rows.append({
            "seed": seed, "condition": "demand_response" if demand_response else "fixed",
            "scenario": summary["scenario"], "input_sha256": comparison["input_sha256"],
            "p2p_energy_kwh": m["p2p_energy_kwh"],
            "p2p_share_of_surplus_pct": m["p2p_share_pct"],
            "p2p_share_of_pv_pct": 100 * m["p2p_energy_kwh"] / m["pv_generation_kwh"],
            "grid_imports_kwh": m["grid_imports_kwh"], "grid_exports_kwh": m["grid_exports_kwh"],
            "household_net_cost_eur": m["household_net_cost_eur"],
            "community_including_regulator_net_cost_eur": m["community_including_regulator_net_cost_eur"],
            "regulator_fee_revenue_eur": m["regulator_fee_revenue_eur"],
            "regulator_reward_expenditure_eur": m["regulator_reward_expenditure_eur"],
            "regulator_remaining_funds_eur": m["regulator_remaining_funds_eur"],
            "battery_final_stored_kwh": m["battery_final_stored_kwh"],
            "battery_loss_kwh": m["battery_loss_kwh"],
            "stored_energy_change_kwh": stored_change,
            "community_cost_storage_adjusted_eur": m["community_including_regulator_net_cost_eur"] - value * stored_change,
            "energy_reconciliation_error_kwh": m["energy_reconciliation_error_kwh"],
            "financial_reconciliation_error_eur": m["financial_reconciliation_error_eur"],
        })
    return rows, comparison["input_sha256"]


def summarize(rows: list[dict], seeds: list[int]) -> tuple[list[dict], list[dict]]:
    stats, wins = [], []
    for condition in CONDITIONS:
        for scenario in SCENARIOS:
            subset = [r for r in rows if r["condition"] == condition and r["scenario"] == scenario]
            for kpi in [*KPIS, "p2p_share_of_surplus_pct", "regulator_fee_revenue_eur", "regulator_reward_expenditure_eur",
                        "regulator_remaining_funds_eur", "battery_final_stored_kwh", "battery_loss_kwh"]:
                values = [r[kpi] for r in subset]
                stats.append({"condition": condition, "scenario": scenario, "kpi": kpi, "runs": len(values),
                              "mean": mean(values), "std": stdev(values) if len(values) > 1 else 0.0,
                              "min": min(values), "max": max(values)})
        index = {(r["seed"], r["scenario"]): r for r in rows if r["condition"] == condition}
        for other in ("F", "K"):
            for kpi, higher_better in KPIS.items():
                diffs = [index[s, "L"][kpi] - index[s, other][kpi] for s in seeds]
                better = sum((d > TOLERANCE) if higher_better else (d < -TOLERANCE) for d in diffs)
                worse = sum((d < -TOLERANCE) if higher_better else (d > TOLERANCE) for d in diffs)
                wins.append({"condition": condition, "comparison": f"L vs {other}", "kpi": kpi,
                             "higher_is_better": higher_better, "runs": len(diffs),
                             "mean_difference": mean(diffs), "std_difference": stdev(diffs) if len(diffs) > 1 else 0.0,
                             "l_better_pct": 100 * better / len(diffs), "l_worse_pct": 100 * worse / len(diffs),
                             "tie_pct": 100 * (len(diffs) - better - worse) / len(diffs)})
    return stats, wins


def chart(rows: list[dict], seeds: list[int], directory: Path) -> None:
    import os
    os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "smartgrid-matplotlib"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from src.charts import COLORS
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.titleweight": "bold", "figure.facecolor": "white"})
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2))
    panels = (("p2p_energy_kwh", "L minus other: P2P energy (kWh)"),
              ("community_cost_storage_adjusted_eur", "L minus other: meters + regulator cost,\nstorage-adjusted (EUR)"))
    for axis, (kpi, label) in zip(axes, panels):
        data, labels, colors = [], [], []
        for condition, short in (("fixed", "fixed"), ("demand_response", "DR")):
            index = {(r["seed"], r["scenario"]): r[kpi] for r in rows if r["condition"] == condition}
            for other in ("F", "K"):
                data.append([index[s, "L"] - index[s, other] for s in seeds])
                labels.append(f"vs {other}\n{short}")
                colors.append(COLORS[other])
        box = axis.boxplot(data, patch_artist=True, widths=.55)
        axis.set_xticks(range(1, len(labels) + 1), labels)
        for patch, color in zip(box["boxes"], colors):
            patch.set_facecolor(color)
            patch.set_alpha(.75)
        for position, values in enumerate(data, 1):
            axis.scatter([position] * len(values), values, s=12, color="#19364F", zorder=3)
        axis.axhline(0, color="#555555", linewidth=1)
        axis.set_title(label, fontsize=11)
    fig.text(.02, .015, f"{len(seeds)} seeded communities x 2 demand conditions. Each point is one seed; "
             "positive P2P and negative cost favour L. Storage valued at import tariff x discharge efficiency.",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, .05, 1, 1))
    directory.mkdir(parents=True, exist_ok=True)
    fig.savefig(directory / "robustness.png", dpi=180)
    fig.savefig(directory / "robustness.svg")
    plt.close(fig)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, nargs="+", default=list(range(42, 62)))
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "results" / "robustness")
    parser.add_argument("--no-charts", action="store_true")
    args = parser.parse_args(argv)
    if len(set(args.seeds)) < 10:
        raise SystemExit("Use at least 10 distinct seeds.")
    config = load_configuration(args.config)
    import logging
    logging.basicConfig(level=logging.WARNING)
    rows, hashes = [], {}
    with tempfile.TemporaryDirectory() as tmp:
        for seed in args.seeds:
            for condition, enabled in CONDITIONS.items():
                seed_rows, digest = run_seed(config, seed, enabled, Path(tmp) / f"{seed}_{condition}")
                rows += seed_rows
                hashes[seed, condition] = digest
            print(f"seed {seed}: done")
    if len({hashes[s, "fixed"] for s in args.seeds}) != len(args.seeds):
        raise ValueError("Different seeds produced identical inputs.")
    stats, wins = summarize(rows, args.seeds)
    args.output.mkdir(parents=True, exist_ok=True)
    write_csv(args.output / "runs.csv", rows)
    write_csv(args.output / "summary.csv", stats)
    write_csv(args.output / "l_win_rates.csv", wins)
    write_json(args.output / "robustness.json", {
        "seeds": args.seeds, "scenarios": SCENARIOS, "conditions": list(CONDITIONS),
        "storage_value_eur_kwh": storage_value_eur_kwh(config),
        "notes": ["Within each seed and condition all scenarios share one input hash.",
                  "std is the sample standard deviation across seeds.",
                  "Storage-adjusted cost subtracts the change in stored energy valued at import tariff x discharge efficiency.",
                  "Win rates count strict improvements beyond 1e-6; ties are reported separately."],
        "summary": stats, "l_win_rates": wins})
    if not args.no_charts:
        chart(rows, args.seeds, args.output)
    for w in wins:
        print(f'{w["condition"]:16} {w["comparison"]} {w["kpi"]:44} mean {w["mean_difference"]:+9.3f} '
              f'sd {w["std_difference"]:8.3f}  L better {w["l_better_pct"]:5.1f}%')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
