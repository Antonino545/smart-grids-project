from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from src.blockchain import Blockchain
from src.market import Transaction


def test_ten_miners_pow_linkage_exact_coverage_and_tamper_detection():
    chain = Blockchain()
    assert len(chain.miner_ids) == 10
    trades = [Transaction("t1", 0, "p2p", "S", "B", 2, .15, .02)]
    chain.mine_hour(0, "2026-06-15T00:00:00+02:00", trades)
    chain.mine_hour(1, "2026-06-15T01:00:00+02:00", [])
    assert all(b.hash.startswith("000") for b in chain.blocks)
    assert chain.blocks[1].previous_hash == chain.blocks[0].hash
    assert chain.validate(trades, 2)
    altered = deepcopy(chain)
    altered.blocks[0].transactions[0]["quantity_kwh"] += 1
    assert not altered.validate(trades, 2)
    assert not chain.validate([], 2)
    with pytest.raises(ValueError, match="Duplicate"):
        Blockchain().mine_hour(0, chain.blocks[0].timestamp, trades + trades)


def test_24_hour_chain_and_structural_validation():
    chain = Blockchain()
    start = datetime(2026, 6, 15, tzinfo=timezone.utc)
    for hour in range(24):
        chain.mine_hour(hour, (start + timedelta(hours=hour)).isoformat(), [])
    assert chain.validate([], 24)
    assert all(attempts > 0 for attempts in chain.miner_attempts.values())
    chain.blocks[-1].previous_hash = "f" * 64
    assert not chain.validate([], 24)
