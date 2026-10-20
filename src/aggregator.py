"""Community-wide merit-order matching using midpoint prices."""

from src.market import Offer, TOLERANCE, Transaction, transfer_energy


def trade_aggregator(offers: list[Offer], hour: int) -> list[Transaction]:
    buyers = sorted((o for o in offers if o.balance_kwh < -TOLERANCE),
                    key=lambda o: (-o.bid_eur_kwh, o.household_id))
    sellers = sorted((o for o in offers if o.balance_kwh > TOLERANCE),
                     key=lambda o: (o.ask_eur_kwh, o.household_id))
    transactions = []
    seller_index = 0
    for buyer in buyers:
        while buyer.balance_kwh < -TOLERANCE and seller_index < len(sellers):
            seller = sellers[seller_index]
            if buyer.bid_eur_kwh + TOLERANCE < seller.ask_eur_kwh:
                break
            quantity = min(-buyer.balance_kwh, seller.balance_kwh)
            transfer_energy(buyer, seller, quantity)
            transactions.append(Transaction(
                f"agg-{hour:03d}-{len(transactions):05d}", hour, "aggregator",
                seller.household_id, buyer.household_id, quantity,
                (buyer.bid_eur_kwh + seller.ask_eur_kwh) / 2,
            ))
            if seller.balance_kwh <= TOLERANCE:
                seller_index += 1
    return transactions
