"""CSV/JSON exports, with data provenance and exact configuration alongside results."""

import csv
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from src.forecasting import HourlyInput
from src.metrics import calculate_metrics
from src.market import Transaction
from src.simulator import SimulationResult


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        columns = fieldnames or (list(rows[0]) if rows else [])
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def export_result(result: SimulationResult, inputs: list[HourlyInput], directory: Path,
                  configuration: dict | None = None) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    rows = []
    for balance in result.balances:
        row = balance.as_dict()
        trades = [t for t in result.transactions if t.hour == balance.hour]
        for market in ("p2p", "aggregator", "grid"):
            for direction, participant in (("buy", "buyer_id"), ("sell", "seller_id")):
                row[f"{market}_{direction}_kwh"] = sum(
                    t.quantity_kwh for t in trades if t.market == market
                    and getattr(t, participant) == balance.household_id)
        row["net_cost_eur"] = sum(
            (m.amount_eur if m.payer == balance.household_id else 0)
            - (m.amount_eur if m.payee == balance.household_id else 0)
            for m in result.ledger.movements if m.hour == balance.hour)
        rows.append(row)
    write_csv(directory / "household_hourly.csv", rows)
    write_csv(directory / "transactions.csv", [t.as_dict() for t in result.transactions],
              list(Transaction.__dataclass_fields__))
    write_csv(directory / "cash_ledger.csv", result.ledger.as_dicts())
    household_costs = [{"household_id": account, "net_cost_eur": -result.ledger.balance(account)}
                       for account in sorted({b.household_id for b in result.balances})]
    write_csv(directory / "household_costs.csv", household_costs)
    history = result.regulator.history if result.regulator else [
        {"hour": hour, "opening_funds_eur": 0, "reward_rate_eur_kwh": 0,
         "reward_paid_eur": 0, "grid_fees_eur": 0, "closing_funds_eur": 0}
        for hour in sorted({b.hour for b in result.balances})]
    write_csv(directory / "regulator_hourly.csv", history)
    write_json(directory / "reward_reservations.json",
               result.regulator.reservation_records() if result.regulator else [])
    if result.blockchain:
        write_json(directory / "blockchain.json", result.blockchain.as_dict())
    hourly = []
    for hour in sorted({b.hour for b in result.balances}):
        balances = [b for b in result.balances if b.hour == hour]
        entry = {"hour": hour, "timestamp": balances[0].timestamp}
        for field in ("pv_kwh", "demand_kwh", "charge_kwh", "discharge_kwh", "stored_end_kwh"):
            entry[field] = sum(getattr(b, field) for b in balances)
        for market in ("p2p", "aggregator"):
            entry[f"{market}_kwh"] = sum(t.quantity_kwh for t in result.transactions if t.hour == hour and t.market == market)
        entry["regulator_funds_eur"] = history[hour]["closing_funds_eur"]
        hourly.append(entry)
    write_csv(directory / "community_hourly.csv", hourly)
    input_json = json.dumps([asdict(row) for row in inputs], sort_keys=True, allow_nan=False)
    summary = {"scenario": result.name, "battery_strategy": result.battery_strategy, "metrics": calculate_metrics(result),
               "input_sha256": hashlib.sha256(input_json.encode()).hexdigest(),
               "input_sources": {key: sorted({getattr(row, key) for row in inputs})
                                 for key in ("weather_source", "demand_source", "price_source")},
               "configuration": configuration or {}}
    write_json(directory / "summary.json", summary)
    return summary
