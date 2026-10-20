"""One SHA-256 proof-of-work block per hour, with round-robin simulated miners."""

import hashlib
import json
from dataclasses import asdict, dataclass
from math import isfinite

from config.settings import BlockchainSettings
from src.forecasting import parse_timestamp
from src.market import Transaction


@dataclass
class Block:
    hour: int
    timestamp: str
    previous_hash: str
    transactions: list[dict]
    miner_id: str
    nonce: int
    hash: str = ""

    def calculate_hash(self) -> str:
        payload = asdict(self)
        del payload["hash"]
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return hashlib.sha256(encoded).hexdigest()


def valid_transaction(record: dict, hour: int) -> bool:
    expected_keys = set(Transaction.__dataclass_fields__)
    if set(record) != expected_keys:
        return False
    return (
        record["hour"] == hour and record["market"] in {"p2p", "aggregator"}
        and all(isinstance(record[key], str) and record[key] for key in
                ("transaction_id", "buyer_id", "seller_id"))
        and record["buyer_id"] != record["seller_id"]
        and "external_grid" not in (record["buyer_id"], record["seller_id"])
        and all(isinstance(record[key], (int, float)) and isfinite(record[key]) for key in
                ("quantity_kwh", "price_eur_kwh", "reward_eur"))
        and record["quantity_kwh"] > 0 and record["price_eur_kwh"] >= 0 and record["reward_eur"] >= 0
        and (record["market"] == "p2p" or record["reward_eur"] == 0)
    )


class Blockchain:
    def __init__(self, settings: BlockchainSettings | None = None):
        self.settings = settings or BlockchainSettings()
        self.miner_ids = [f"miner-{index + 1:02d}" for index in range(self.settings.miner_count)]
        self.miner_attempts = dict.fromkeys(self.miner_ids, 0)
        self.blocks: list[Block] = []

    def mine_hour(self, hour: int, timestamp: str, transactions: list[Transaction]) -> Block:
        if hour != len(self.blocks):
            raise ValueError("Blocks must represent consecutive hours starting from zero.")
        parse_timestamp(timestamp)
        records = [transaction.as_dict() for transaction in transactions]
        if any(not valid_transaction(record, hour) for record in records):
            raise ValueError("Invalid internal-market transaction.")
        existing_ids = {t["transaction_id"] for b in self.blocks for t in b.transactions}
        new_ids = [t["transaction_id"] for t in records]
        if len(new_ids) != len(set(new_ids)) or existing_ids.intersection(new_ids):
            raise ValueError("Duplicate on-chain transaction ID.")
        block = Block(hour, timestamp, self.blocks[-1].hash if self.blocks else "0" * 64,
                      records, self.miner_ids[0], 0)
        # Serialize unchanged transaction data once; only miner and nonce vary per attempt.
        suffix = json.dumps({"previous_hash": block.previous_hash, "timestamp": block.timestamp,
                             "transactions": block.transactions}, sort_keys=True,
                            separators=(",", ":"), allow_nan=False)[1:].encode()
        prefixes = {miner: f'{{"hour":{hour},"miner_id":"{miner}","nonce":'.encode()
                    for miner in self.miner_ids}
        for nonce in range(self.settings.max_nonce_attempts):
            miner = self.miner_ids[nonce % len(self.miner_ids)]
            self.miner_attempts[miner] += 1
            block.miner_id, block.nonce = miner, nonce
            digest = hashlib.sha256(prefixes[miner] + str(nonce).encode() + b"," + suffix).hexdigest()
            if digest.startswith(self.settings.hash_prefix):
                block.hash = digest
                self.blocks.append(block)
                return block
        raise RuntimeError("Mining attempt limit reached; no unverified block was appended.")

    def validate(self, expected_transactions: list[Transaction] | None = None,
                 expected_hours: int | None = None) -> bool:
        try:
            if expected_hours is not None and len(self.blocks) != expected_hours:
                return False
            previous_hash, previous_time = "0" * 64, None
            recorded = {}
            for hour, block in enumerate(self.blocks):
                timestamp = parse_timestamp(block.timestamp)
                if (block.hour != hour or block.previous_hash != previous_hash
                        or (previous_time is not None and timestamp <= previous_time)
                        or type(block.nonce) is not int or block.nonce < 0
                        or block.miner_id != self.miner_ids[block.nonce % len(self.miner_ids)]
                        or block.hash != block.calculate_hash()
                        or not block.hash.startswith(self.settings.hash_prefix)):
                    return False
                for record in block.transactions:
                    if not valid_transaction(record, hour) or record["transaction_id"] in recorded:
                        return False
                    recorded[record["transaction_id"]] = record
                previous_hash, previous_time = block.hash, timestamp
            if expected_transactions is not None:
                internal = [t for t in expected_transactions if t.market in {"p2p", "aggregator"}]
                expected = {t.transaction_id: t.as_dict() for t in internal}
                if len(expected) != len(internal) or recorded != expected:
                    return False
            return True
        except (ValueError, TypeError, KeyError, AttributeError, IndexError):
            return False

    def as_dict(self) -> dict:
        return {"settings": asdict(self.settings), "miner_ids": self.miner_ids,
                "miner_attempts": self.miner_attempts,
                "blocks": [asdict(block) for block in self.blocks]}
