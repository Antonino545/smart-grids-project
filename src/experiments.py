"""Controlled scenario comparison using one immutable community and one input dataset."""

from dataclasses import asdict, replace
from pathlib import Path

from src.charts import generate_charts
from src.community_map import generate_community_map
from src.building_charts import generate_building_charts
from src.forecasting import export_inputs, generate_inputs
from src.households import export_households, generate_households
from src.output import export_result, write_csv, write_json
from src.simulator import run_simulation
from config.demand_response import DemandResponseSettings
from src.demand_response import shift_demand

SCENARIOS = {
    "A": (True, False, "self_consumption_first"),
    "B": (True, True, "self_consumption_first"),
    "C": (False, False, "self_consumption_first"),
    "D": (False, True, "self_consumption_first"),
    "E": (True, False, "p2p_priority"),
    "F": (True, True, "p2p_priority"),
    # Regulator policy variants of B (batteries on, regulated, self-consumption first).
    "G": (True, True, "self_consumption_first"),
    "H": (True, True, "self_consumption_first"),
    "I": (True, True, "self_consumption_first"),
    "J": (True, True, "self_consumption_first"),
    "K": (True, True, "self_consumption_first"),
}
PRIORITY_SCENARIOS = ["E", "F"]
POLICY_SCENARIOS = ["G", "H", "I", "J", "K"]
# Each policy scenario changes one regulator rule relative to B. G and H are sized so that,
# on the default Turin day, fees and rewards would roughly balance (B: 18,067 grid kWh,
# 2,350 P2P kWh): fee 0.01 x 18,067 / 2,350 / 0.02 -> fee 0.0025; or reward 0.075.
REGULATOR_OVERRIDES = {
    "G": {"grid_fee_eur_kwh": 0.0025},                                   # lower fee
    "H": {"lower_reward_eur_kwh": 0.0375, "upper_reward_eur_kwh": 0.075},  # bigger reward
    "I": {"fee_scope": "missed_local"},                                  # fee only on missed local trades
    "J": {"refund_leftover": True},                                      # end-of-day refund to P2P traders
    "K": {"reward_mode": "budget_sized"},                                # reward sized to the fund
}
SCENARIO_DESCRIPTIONS = {
    "G": "B with a lower grid fee (EUR 0.0025/kWh)",
    "H": "B with a bigger reward (EUR 0.075/kWh upper tier, 0.0375 lower)",
    "I": "B, fee only on grid energy a neighbour could have traded",
    "J": "B, leftover fund refunded to P2P traders at day end",
    "K": "B, reward rate sized each hour to spend the fund",
}


def run_experiments(config: dict, output: Path, scenario_names: list[str], charts: bool = True) -> dict:
    settings = config["simulation"]
    households = generate_households(settings, config["households"], config.get("buildings"))
    inputs = generate_inputs(households, settings, config["forecast"])
    response = config.get("demand_response", DemandResponseSettings())
    baseline_inputs = inputs
    inputs, shifts = shift_demand(households, inputs, response, config.get("buildings"))
    if response.enabled:
        export_inputs(baseline_inputs, output / "inputs" / "hourly_inputs_baseline.csv")
        # Always write a header, including a valid zero-shift experiment.
        import csv
        path = output / "inputs" / "demand_shifts.csv"
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["household_id", "building_type", "source_hour", "target_hour",
                                                       "source_timestamp", "target_timestamp", "quantity_kwh"])
            writer.writeheader()
            writer.writerows(shifts)
    export_households(households, output / "inputs" / "households.csv")
    export_inputs(inputs, output / "inputs" / "hourly_inputs.csv")
    results, summaries = [], []
    for name in scenario_names:
        battery, regulated, strategy = SCENARIOS[name]
        overrides = REGULATOR_OVERRIDES.get(name, {})
        regulator_settings = replace(config["regulator"], **overrides)
        result = run_simulation(
            households, inputs, replace(settings, household_count=len(households)), config["market"], name,
            batteries_enabled=battery, regulation_enabled=regulated,
            regulator_settings=regulator_settings, blockchain_settings=config["blockchain"],
            battery_strategy=strategy)
        configuration = {key: asdict(value) for key, value in config.items()}
        configuration["regulator"] = asdict(regulator_settings)
        configuration["experiment"] = {"batteries_enabled": battery, "regulation_enabled": regulated,
                                        "battery_strategy": strategy, "regulator_overrides": overrides}
        summaries.append(export_result(result, inputs, output / name, configuration))
        results.append(result)
    if len({s["input_sha256"] for s in summaries}) != 1:
        raise ValueError("Scenarios do not share identical hourly inputs.")
    from collections import Counter
    community = {"participant_unit": "aggregated_building_meter" if config["buildings"].enabled else "household",
                 "participant_count": len(households), "home_count": sum(h.homes for h in households),
                 "building_type_counts": dict(Counter(h.building_type for h in households)),
                 "battery_owner_count": sum(h.has_battery for h in households)}
    community["prosumer_count"] = sum(h.participant_role == "prosumer" for h in households)
    community["consumer_count"] = sum(h.participant_role == "consumer" for h in households)
    comparison = {"community": community, "input_sha256": summaries[0]["input_sha256"], "scenarios": summaries,
                  "demand_response": {"enabled": response.enabled, "shifted_energy_kwh": sum(s["quantity_kwh"] for s in shifts),
                                      "shifted_meter_count": len({s["household_id"] for s in shifts}),
                                      "eligibility": "PV prosumers without battery ownership, unchanged across A-F"},
                  "notes": ["Default weather, demand and price history are synthetic, not measurements.",
                            "Building archetypes and parameter ranges are illustrative engineering assumptions.",
                            "C and D retain ownership metadata but disable all battery operations.",
                            "E and F sell PV via P2P before charging remaining owner PV.",
                            *(f"{name}: {SCENARIO_DESCRIPTIONS[name]}." for name in scenario_names if name in SCENARIO_DESCRIPTIONS),
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
    policy = [name for name in POLICY_SCENARIOS if name in metrics]
    if policy and "B" in metrics:
        lines += ["", "## Regulator policy variants (each compared with B)", "",
                  "| Scenario | Change | P2P kWh vs B | Fees EUR | Rewards EUR | Refunds EUR | Fund left EUR | Household cost vs B EUR |",
                  "|---|---|---:|---:|---:|---:|---:|---:|"]
        for name in ["B"] + policy:
            m, b = metrics[name], metrics["B"]
            lines.append(f'| {name} | {SCENARIO_DESCRIPTIONS.get(name, "reference")} | {m["p2p_energy_kwh"] - b["p2p_energy_kwh"]:+.3f} | '
                         f'{m["regulator_fee_revenue_eur"]:.2f} | {m["regulator_reward_expenditure_eur"]:.2f} | {m["regulator_refund_eur"]:.2f} | '
                         f'{m["regulator_remaining_funds_eur"]:.2f} | {m["household_net_cost_eur"] - b["household_net_cost_eur"]:+.2f} |')
    lines += ["", "Price guidance and funded discounts can make more offers compatible. A reward cannot create PV surplus or demand, and does not guarantee improvement for other seeds or inputs.",
              "", "## Battery interpretation", "",
              "Self-consumption-first batteries remove PV surplus before trading and reduce later demand. Compare absolute P2P energy alongside its changing denominator. E/F defer charging until after P2P, so their offered-surplus denominator includes PV subsequently stored. Compare raw PV surplus as well.",
              "", "Initial stored battery energy is an exogenous inventory. Final stored energy can differ between strategies. Costs exclude inventory valuation, battery investment, degradation, taxes and network charges other than the modeled regulator fee.",
              "", "## Accounting and limits", "",
              "Internal payments transfer money between households. Fees transfer money to the regulator, and rewards transfer it back. Household net costs include these transfers. Household-plus-regulator net costs equal net external-grid payments. Every summary reports numerical energy and financial reconciliation errors.",
              "", "The model uses copper-plate energy settlement without feeder limits, voltage, power flow, battery aging or strategic learning. A single deterministic day supports a demonstration, not a statistical claim. No improvement is forced."]
    path.write_text("\n".join(lines) + "\n")
