"""Run reproducible community scenarios and export reconciled results."""

import argparse
import json
import logging
from pathlib import Path

from config.buildings import load_building_settings
from config.settings import (
    BatterySettings, BlockchainSettings, ForecastSettings, HouseholdSettings,
    MarketSettings, RegulatorSettings, SimulationSettings,
)
from src.experiments import run_experiments

LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent


def load_configuration(path: Path | None) -> dict:
    raw = json.loads(path.read_text()) if path else {}
    constructors = {"simulation": SimulationSettings, "households": HouseholdSettings,
                    "forecast": ForecastSettings, "market": MarketSettings,
                    "regulator": RegulatorSettings, "blockchain": BlockchainSettings, "buildings": load_building_settings}
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
    parser.add_argument("--scenario", choices=["all", "A", "B", "C", "D", "E", "F"], default="all")
    parser.add_argument("--include-priority", action="store_true", help="Add E/F P2P-priority comparisons to all scenarios")
    parser.add_argument("--no-charts", action="store_true", help="Skip image generation")
    args = parser.parse_args(argv)
    try:
        config = load_configuration(args.config)
        settings = config["simulation"]
        logging.basicConfig(level=settings.log_level, format="%(levelname)s | %(name)s | %(message)s")
        names = (["A", "B", "C", "D"] + (["E", "F"] if args.include_priority else [])) if args.scenario == "all" else [args.scenario]
        if args.include_priority and args.scenario != "all":
            raise ValueError("--include-priority is used with --scenario all.")
        comparison = run_experiments(config, args.output, names, charts=not args.no_charts)
        for summary in comparison["scenarios"]:
            LOGGER.info("Simulation %s complete: %d buildings/meters, %d hours; P2P %.3f kWh; blockchain valid=%s.",
                        summary["scenario"], settings.household_count, settings.hours,
                        summary["metrics"]["p2p_energy_kwh"], summary["metrics"]["blockchain_valid"])
        LOGGER.info("Results: %s", args.output.resolve())
        return 0
    except (ValueError, TypeError, KeyError, OSError, RuntimeError) as error:
        LOGGER.error("Simulation failed: %s", error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
