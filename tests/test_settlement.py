from config.settings import MarketSettings, SimulationSettings
from src.aggregator import trade_aggregator
from src.external_grid import settle_grid
from src.forecasting import generate_inputs
from src.households import generate_households
from src.ledger import Ledger
from src.market import Offer
from src.simulator import run_simulation

import pytest


def test_aggregator_priorities_midpoint_and_cross_group():
    offers = [Offer("B1", 1, -3, .25, .3), Offer("B2", 2, -3, .20, .3),
              Offer("S1", 3, 2, .1, .10), Offer("S2", 4, 3, .1, .22)]
    trades = trade_aggregator(offers, 0)
    assert [(t.buyer_id, t.seller_id, t.quantity_kwh) for t in trades] == [("B1", "S1", 2), ("B1", "S2", 1)]
    assert trades[0].price_eur_kwh == pytest.approx(.175)
    assert trades[1].price_eur_kwh == pytest.approx(.235)
    grid = settle_grid(offers, 0, MarketSettings())
    assert all(o.balance_kwh == 0 for o in offers)
    assert sum(t.quantity_kwh for t in grid) == 5
    ledger = Ledger()
    for t in trades + grid:
        ledger.record_trade(t)
    ledger.verify()
    assert ledger.balance("B1") == pytest.approx(-2 * .175 - .235)


def test_full_day_without_regulator_or_blockchain():
    settings = SimulationSettings()
    households = generate_households(settings)
    inputs = generate_inputs(households, settings)
    result = run_simulation(households, inputs, settings)
    assert len(result.balances) == 2400
    assert {t.market for t in result.transactions} == {"p2p", "aggregator", "grid"}
    assert result.transactions == run_simulation(households, inputs, settings).transactions
    assert len({t.transaction_id for t in result.transactions}) == len(result.transactions)
    result.ledger.verify()
