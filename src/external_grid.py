"""Settle every remaining household shortage/surplus with the external grid."""

from config.settings import MarketSettings
from src.market import Offer, TOLERANCE, Transaction

GRID_ACCOUNT = "external_grid"


def settle_grid(offers: list[Offer], hour: int, settings: MarketSettings) -> list[Transaction]:
    transactions = []
    for offer in offers:
        if abs(offer.balance_kwh) > TOLERANCE:
            exporting = offer.balance_kwh > 0
            transactions.append(Transaction(
                f"grid-{hour:03d}-{len(transactions):05d}", hour, "grid",
                offer.household_id if exporting else GRID_ACCOUNT,
                GRID_ACCOUNT if exporting else offer.household_id,
                abs(offer.balance_kwh),
                settings.grid_export_tariff_eur_kwh if exporting else settings.grid_import_tariff_eur_kwh,
            ))
        offer.balance_kwh = 0.0
    return transactions
