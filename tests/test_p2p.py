from random import Random

import pytest

from src.market import Offer, transfer_energy
from src.p2p_market import trade_p2p


def test_neighborhood_limits_price_and_multiple_trades():
    offers = [Offer("B", 1, -5, .2, .3), Offer("S1", 1, 2, .1, .15),
              Offer("S2", 1, 4, .1, .18), Offer("S3", 2, 5, .1, .1)]
    trades = trade_p2p(offers, 0, Random(42))
    assert sum(t.quantity_kwh for t in trades) == 5
    assert {t.seller_id for t in trades} == {"S1", "S2"}
    asks = {o.household_id: o.ask_eur_kwh for o in offers}
    assert all(t.price_eur_kwh == asks[t.seller_id] for t in trades)
    assert offers[0].balance_kwh == 0
    assert all(o.balance_kwh >= 0 for o in offers[1:])
    assert offers[-1].balance_kwh == 5


def test_incompatible_and_reproducible_matching():
    def run():
        return trade_p2p([Offer("B", 1, -2, .2, .3), Offer("S", 1, 3, .1, .15),
                          Offer("expensive", 1, 1, .1, .25)], 0, Random(42))
    assert run() == run()
    assert all(t.seller_id != "expensive" for t in run())


def test_overtrading_and_negative_quantities_rejected():
    buyer, seller = Offer("B", 1, -1, .2, .2), Offer("S", 1, 1, .2, .2)
    for quantity in (-1, 0, 2, float("nan")):
        with pytest.raises(ValueError):
            transfer_energy(buyer, seller, quantity)
