"""Verify exported artifacts independently of the in-memory simulation run."""

import argparse
from dataclasses import asdict
import hashlib
import csv
import json
import math
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import BlockchainSettings
from src.blockchain import Block, Blockchain
from src.market import Transaction
from src.forecasting import HourlyInput


def verify_results(directory: Path) -> dict:
    comparison = json.loads((directory / "comparison.json").read_text())
    with (directory / "inputs" / "hourly_inputs.csv").open() as handle:
        inputs = []
        for row in csv.DictReader(handle):
            row["hour"] = int(row["hour"])
            for key in ("irradiance_w_m2", "pv_kwh", "demand_kwh", "reference_price_eur_kwh"):
                row[key] = float(row[key])
            inputs.append(asdict(HourlyInput(**row)))
    actual_hash = hashlib.sha256(json.dumps(inputs, sort_keys=True, allow_nan=False).encode()).hexdigest()
    if actual_hash != comparison["input_sha256"]:
        raise ValueError("Exported hourly inputs do not match the recorded hash")
    hashes = set()
    verified = {}
    for summary in comparison["scenarios"]:
        name = summary["scenario"]
        folder = directory / name
        saved = json.loads((folder / "summary.json").read_text())
        if saved != summary:
            raise ValueError(f"Comparison and scenario summary disagree: {name}")
        hashes.add(summary["input_sha256"])
        with (folder / "transactions.csv").open() as handle:
            transactions = [Transaction(
                row["transaction_id"], int(row["hour"]), row["market"], row["seller_id"], row["buyer_id"],
                float(row["quantity_kwh"]), float(row["price_eur_kwh"]), float(row["reward_eur"]))
                for row in csv.DictReader(handle)]
        raw_chain = json.loads((folder / "blockchain.json").read_text())
        chain = Blockchain(BlockchainSettings(**raw_chain["settings"]))
        chain.blocks = [Block(**block) for block in raw_chain["blocks"]]
        if raw_chain["miner_ids"] != chain.miner_ids:
            raise ValueError("Exported miner identities disagree with configuration")
        hours = summary["configuration"]["simulation"]["hours"]
        if not chain.validate(transactions, hours):
            raise ValueError(f"Invalid exported chain/journal: {name}")
        with (folder / "cash_ledger.csv").open() as handle:
            movements = list(csv.DictReader(handle))
        for transaction in transactions:
            payments = [m for m in movements if m["transaction_id"] == transaction.transaction_id
                        and m["kind"] == transaction.market]
            if (len(payments) != 1 or payments[0]["payer"] != transaction.buyer_id
                    or payments[0]["payee"] != transaction.seller_id
                    or abs(float(payments[0]["amount_eur"]) - transaction.value_eur) > 1e-8):
                raise ValueError("Transaction payment disagrees with cash ledger")
            rewards = [m for m in movements if m["transaction_id"] == transaction.transaction_id and m["kind"] == "reward"]
            if len(rewards) != int(transaction.reward_eur > 0) or abs(sum(float(m["amount_eur"]) for m in rewards) - transaction.reward_eur) > 1e-8:
                raise ValueError("Transaction reward disagrees with cash ledger")
        balances = {}
        for movement in movements:
            amount = float(movement["amount_eur"])
            if not math.isfinite(amount) or amount < 0:
                raise ValueError("Invalid cash movement")
            balances[movement["payer"]] = balances.get(movement["payer"], 0) - amount
            balances[movement["payee"]] = balances.get(movement["payee"], 0) + amount
        if abs(sum(balances.values())) > 1e-7:
            raise ValueError(f"Unbalanced exported ledger: {name}")
        with (folder / "household_hourly.csv").open() as handle:
            rows = list(csv.DictReader(handle))
        count = summary["configuration"]["simulation"]["household_count"]
        if len(rows) != hours * count:
            raise ValueError(f"Incomplete exported household data: {name}")
        for row in rows:
            buys = sum(float(row[f"{market}_buy_kwh"]) for market in ("p2p", "aggregator", "grid"))
            sales = sum(float(row[f"{market}_sell_kwh"]) for market in ("p2p", "aggregator", "grid"))
            error = (float(row["pv_kwh"]) + float(row["discharge_kwh"]) + buys
                     - float(row["demand_kwh"]) - float(row["charge_kwh"]) - sales)
            if not math.isfinite(error) or abs(error) > 1e-8:
                raise ValueError(f"Exported household energy imbalance: {name}")
        expected_fund = summary["metrics"]["regulator_remaining_funds_eur"]
        if abs(balances.get("regulator", 0) - expected_fund) > 1e-7:
            raise ValueError(f"Exported fund disagrees with ledger: {name}")
        verified[name] = {"hours": hours, "internal_trades": sum(t.market != "grid" for t in transactions),
                          "blockchain_valid": True, "cash_and_energy_valid": True}
    if hashes != {comparison["input_sha256"]}:
        raise ValueError("Scenario input hashes differ")
    return verified


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", type=Path, default=PROJECT_ROOT / "results")
    args = parser.parse_args()
    print(json.dumps(verify_results(args.directory), indent=2))
