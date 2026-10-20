"""Random matching within neighborhoods; each buyer tries every eligible seller."""

from random import Random
from typing import TYPE_CHECKING

from src.market import Offer, TOLERANCE, Transaction, transfer_energy

if TYPE_CHECKING:
    from src.regulator import Regulator


def trade_p2p(offers: list[Offer], hour: int, rng: Random,
              regulator: "Regulator | None" = None) -> list[Transaction]:
    transactions = []
    for group in sorted({offer.group_id for offer in offers}):
        buyers = [o for o in offers if o.group_id == group and o.balance_kwh < -TOLERANCE]
        sellers = [o for o in offers if o.group_id == group and o.balance_kwh > TOLERANCE]
        rng.shuffle(buyers)
        for buyer in buyers:
            candidates = sellers.copy()
            rng.shuffle(candidates)
            for seller in candidates:
                quantity = min(-buyer.balance_kwh, seller.balance_kwh)
                if quantity <= TOLERANCE:
                    continue
                price, reward, reservation = seller.ask_eur_kwh, 0.0, None
                bid = buyer.bid_eur_kwh
                if regulator is not None:
                    bid, price, reward, reservation = regulator.quote(buyer, seller, quantity)
                if bid + TOLERANCE < price:
                    if reservation is not None:
                        regulator.release(reservation)
                    continue
                transfer_energy(buyer, seller, quantity)
                transaction = Transaction(f"p2p-{hour:03d}-{len(transactions):05d}", hour, "p2p",
                                          seller.household_id, buyer.household_id, quantity, price, reward)
                if reservation is not None:
                    regulator.pay(reservation, transaction.transaction_id)
                transactions.append(transaction)
    return transactions
