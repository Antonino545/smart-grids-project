"""Demand-only additions must mix locally without redrawing original prosumers."""

from collections import Counter
from dataclasses import replace

import pytest

from config.buildings import BuildingSettings
from config.settings import SimulationSettings
from main import load_configuration
from src.community_map import community_layout
from src.forecasting import generate_inputs
from src.households import generate_households
from src.simulator import run_simulation
from src.metrics import calculate_metrics


def test_fifty_consumers_are_mixed_and_original_prosumers_are_unchanged():
    settings = SimulationSettings(hours=48)
    original = generate_households(settings)
    extended = generate_households(settings, buildings=BuildingSettings(consumer_count=50))
    assert extended[:100] == original
    consumers = extended[100:]
    assert len(extended) == len({h.household_id for h in extended}) == 150
    assert Counter(h.building_type for h in consumers) == {
        "small_house": 25, "apartment_block": 15, "supermarket": 5, "school": 5}
    assert all(h.participant_role == "consumer" and h.pv_capacity_kw == 0 and h.battery is None for h in consumers)
    for group in range(1, 11):
        assert Counter(h.participant_role for h in extended if h.group_id == group) == {"prosumer": 10, "consumer": 5}
    inputs = generate_inputs(extended, settings)
    assert [r for r in inputs if int(r.household_id[1:]) <= 100] == generate_inputs(original, settings)
    assert all(r.pv_kwh == 0 for r in inputs if int(r.household_id[1:]) > 100)
    cells = community_layout(extended)
    assert len(cells) == 150
    # Display shuffling mixes roles across columns, rather than isolating consumers.
    assert any(c["participant_role"] == "consumer" and c["column"] < 10 for c in cells)


def test_added_consumers_buy_but_never_sell_and_energy_is_conserved():
    config = load_configuration(None)
    hs = generate_households(config["simulation"], config["households"], config["buildings"])
    consumer_ids = {h.household_id for h in hs if h.participant_role == "consumer"}
    result = run_simulation(hs, generate_inputs(hs, config["simulation"], config["forecast"]),
                            replace(config["simulation"], household_count=len(hs)), config["market"],
                            blockchain_enabled=False)
    assert any(t.market == "p2p" and t.buyer_id in consumer_ids for t in result.transactions)
    assert not any(t.seller_id in consumer_ids for t in result.transactions)
    assert abs(calculate_metrics(result)["energy_reconciliation_error_kwh"]) < 1e-7


@pytest.mark.parametrize("count", [-1, 2.5, True, 51])
def test_invalid_consumer_counts_are_rejected(count):
    with pytest.raises(ValueError):
        generate_households(SimulationSettings(), buildings=BuildingSettings(consumer_count=count))
