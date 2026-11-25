"""Run reproducible community scenarios and export reconciled results."""

import argparse
import json
import logging
from dataclasses import replace
from pathlib import Path

from config.buildings import load_building_settings
from config.demand_response import DemandResponseSettings
from config.settings import (
    BatterySettings, BlockchainSettings, ForecastSettings, HouseholdSettings,
    MarketSettings, RegulatorSettings, SimulationSettings,
)
from src.experiments import COMBINED_SCENARIOS, POLICY_SCENARIOS, PRIORITY_SCENARIOS, SCENARIOS, run_experiments

LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent


def load_configuration(path: Path | None) -> dict:
    raw = json.loads((PROJECT_ROOT / "config/default.json").read_text())
    if path:
        overrides = json.loads(path.read_text())
        if not isinstance(overrides, dict):
            raise ValueError("Configuration must be a JSON object.")
        def merge(base, extra):
            for key, value in extra.items():
                if isinstance(value, dict) and isinstance(base.get(key), dict):
                    merge(base[key], value)
                else:
                    base[key] = value
        merge(raw, overrides)
    constructors = {"simulation": SimulationSettings, "households": HouseholdSettings,
                    "forecast": ForecastSettings, "market": MarketSettings,
                    "regulator": RegulatorSettings, "blockchain": BlockchainSettings, "buildings": load_building_settings,
                    "demand_response": DemandResponseSettings}
    if not isinstance(raw, dict) or set(raw) - set(constructors):
        raise ValueError("Configuration must be an object with known section names.")
    if any(not isinstance(section, dict) for section in raw.values()):
        raise ValueError("Configuration sections must be JSON objects.")
    if "battery" in raw.get("simulation", {}):
        raw["simulation"]["battery"] = BatterySettings(**raw["simulation"]["battery"])
    return {section: (constructor(raw.get(section, {})) if section == "buildings" else constructor(**raw.get(section, {})))
            for section, constructor in constructors.items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, help="Optional JSON parameter overrides")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "results")
    parser.add_argument("--scenario", choices=["all", *SCENARIOS], default="all")
    parser.add_argument("--include-priority", action="store_true", help="Add E/F P2P-priority comparisons to all scenarios")
    parser.add_argument("--include-policy", action="store_true",
                        help="Add G-K regulator policy variants of B (lower fee, bigger reward, targeted fee, refund, sized reward)")
    parser.add_argument("--include-combined", action="store_true",
                        help="Add scenario L: F (P2P before charging, regulated) with K's fund-sized reward")
    parser.add_argument("--no-charts", action="store_true", help="Skip image generation")
    parser.add_argument("--compare-demand-response", action="store_true", help="Compare fixed demand with PV-aware shifting in a separate subfolder")
    args = parser.parse_args(argv)
    try:
        config = load_configuration(args.config)
        settings = config["simulation"]
        logging.basicConfig(level=settings.log_level, format="%(levelname)s | %(name)s | %(message)s")
        names = (["A", "B", "C", "D"] + (PRIORITY_SCENARIOS if args.include_priority else [])
                 + (POLICY_SCENARIOS if args.include_policy else [])
                 + (COMBINED_SCENARIOS if args.include_combined else [])) if args.scenario == "all" else [args.scenario]
        if (args.include_priority or args.include_policy or args.include_combined) and args.scenario != "all":
            raise ValueError("--include-priority, --include-policy and --include-combined are used with --scenario all.")
        if args.compare_demand_response:
            config["demand_response"] = replace(config["demand_response"], enabled=False)
        comparison = run_experiments(config, args.output, names, charts=not args.no_charts)
        if args.compare_demand_response:
            from src.demand_response_charts import compare_demand_response
            flexible = {**config, "demand_response": replace(config["demand_response"], enabled=True)}
            shifted = run_experiments(flexible, args.output / "demand_response", names, charts=not args.no_charts)
            compare_demand_response(comparison, shifted, args.output, charts=not args.no_charts)
            LOGGER.info("Demand response moved %.3f kWh across %d meters; results: %s",
                        shifted["demand_response"]["shifted_energy_kwh"], shifted["demand_response"]["shifted_meter_count"],
                        args.output / "demand_response")
        for summary in comparison["scenarios"]:
            LOGGER.info("Simulation %s complete: %d buildings/meters, %d hours; P2P %.3f kWh; blockchain valid=%s.",
                        summary["scenario"], comparison["community"]["participant_count"], settings.hours,
                        summary["metrics"]["p2p_energy_kwh"], summary["metrics"]["blockchain_valid"])
        LOGGER.info("Results: %s", args.output.resolve())
        return 0
    except (ValueError, TypeError, KeyError, OSError, RuntimeError) as error:
        LOGGER.error("Simulation failed: %s", error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
