"""Controlled scenario comparison using one immutable community and one input dataset."""

from dataclasses import asdict
from pathlib import Path

from src.charts import generate_charts
from src.community_map import generate_community_map
from src.building_charts import generate_building_charts
from src.forecasting import export_inputs, generate_inputs
from src.households import export_households, generate_households
from src.output import export_result, write_csv, write_json
from src.simulator import run_simulation

SCENARIOS = {
    "A": (True, False, "self_consumption_first"),
    "B": (True, True, "self_consumption_first"),
    "C": (False, False, "self_consumption_first"),
    "D": (False, True, "self_consumption_first"),
    "E": (True, False, "p2p_priority"),
    "F": (True, True, "p2p_priority"),
}


def run_experiments(config: dict, output: Path, scenario_names: list[str], charts: bool = True) -> dict:
    settings = config["simulation"]
    households = generate_households(settings, config["households"], config.get("buildings"))
    inputs = generate_inputs(households, settings, config["forecast"])
    export_households(households, output / "inputs" / "households.csv")
    export_inputs(inputs, output / "inputs" / "hourly_inputs.csv")
    results, summaries = [], []
    for name in scenario_names:
        battery, regulated, strategy = SCENARIOS[name]
        result = run_simulation(
            households, inputs, settings, config["market"], name,
            batteries_enabled=battery, regulation_enabled=regulated,
            regulator_settings=config["regulator"], blockchain_settings=config["blockchain"],
            battery_strategy=strategy)
        configuration = {key: asdict(value) for key, value in config.items()}
        configuration["experiment"] = {"batteries_enabled": battery, "regulation_enabled": regulated,
                                        "battery_strategy": strategy}
        summaries.append(export_result(result, inputs, output / name, configuration))
        results.append(result)
    if len({s["input_sha256"] for s in summaries}) != 1:
        raise ValueError("Scenarios do not share identical hourly inputs.")
    from collections import Counter
    community = {"participant_unit": "aggregated_building_meter" if config["buildings"].enabled else "household",
                 "participant_count": len(households), "dwelling_count": sum(h.dwelling_units for h in households),
                 "building_type_counts": dict(Counter(h.building_type for h in households)),
                 "battery_owner_count": sum(h.has_battery for h in households)}
    comparison = {"community": community, "input_sha256": summaries[0]["input_sha256"], "scenarios": summaries,
                  "notes": ["Default weather, demand and price history are synthetic, not measurements.",
                            "Building archetypes and parameter ranges are illustrative engineering assumptions.",
                            "C and D retain ownership metadata but disable all battery operations.",
                            "E and F sell PV via P2P before charging remaining owner PV.",
                            "P2P-priority denominator is surplus available before P2P, before deferred charging.",
                            "Costs exclude battery capital/degradation and inventory valuation; initial/final stored energy is reported."]}
    write_json(output / "comparison.json", comparison)
    write_csv(output / "comparison.csv", [{"scenario": s["scenario"], "battery_strategy": s["battery_strategy"],
                                          **s["metrics"]} for s in summaries])
    if charts:
        generate_charts(results, output / "charts")
        generate_community_map(households, output / "charts")
        generate_building_charts(households, inputs, output / "charts")
    write_discussion(comparison, output / "discussion.md")
    return comparison


def write_discussion(comparison: dict, path: Path) -> None:
    metrics = {s["scenario"]: s["metrics"] for s in comparison["scenarios"]}
    lines = ["# Experiment discussion", "", "These are model outputs for the recorded inputs and assumptions, not evidence of real-world performance.", "",
             "| Scenario | P2P kWh | P2P share % | Imports kWh | Exports kWh | Household net cost EUR |", 
             "|---|---:|---:|---:|---:|---:|"]
    for name, metric in metrics.items():
        share = f'{metric["p2p_share_pct"]:.3f}' if metric["p2p_share_pct"] is not None else "undefined"
        lines.append(f'| {name} | {metric["p2p_energy_kwh"]:.3f} | {share} | {metric["grid_imports_kwh"]:.3f} | {metric["grid_exports_kwh"]:.3f} | {metric["household_net_cost_eur"]:.3f} |')
    lines += ["", "## Regulation comparisons"]
    for base, regulated in (("A", "B"), ("C", "D"), ("E", "F")):
        if base in metrics and regulated in metrics:
            delta = metrics[regulated]["p2p_energy_kwh"] - metrics[base]["p2p_energy_kwh"]
            direction = "increased" if delta > 1e-9 else "decreased" if delta < -1e-9 else "did not change"
            lines.append(f"- {regulated} versus {base}: regulation {direction} P2P energy (difference {delta:+.3f} kWh).")
    lines += ["", "Price guidance and funded discounts can make more offers compatible. A reward cannot create PV surplus or demand, and does not guarantee improvement for other seeds or inputs.",
              "", "## Battery interpretation", "",
              "Self-consumption-first batteries remove PV surplus before trading and reduce later demand. Compare absolute P2P energy alongside its changing denominator. E/F defer charging until after P2P, so their offered-surplus denominator includes PV subsequently stored. Compare raw PV surplus as well.",
              "", "Initial stored battery energy is an exogenous inventory. Final stored energy can differ between strategies. Costs exclude inventory valuation, battery investment, degradation, taxes and network charges other than the modeled regulator fee.",
              "", "## Accounting and limits", "",
              "Internal payments transfer money between households. Fees transfer money to the regulator, and rewards transfer it back. Household net costs include these transfers. Household-plus-regulator net costs equal net external-grid payments. Every summary reports numerical energy and financial reconciliation errors.",
              "", "The model uses copper-plate energy settlement without feeder limits, voltage, power flow, battery aging or strategic learning. A single deterministic day supports a demonstration, not a statistical claim. No improvement is forced."]
    path.write_text("\n".join(lines) + "\n")
