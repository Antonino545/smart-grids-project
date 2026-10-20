"""Shared market records; positive balances sell, negative balances buy."""

from dataclasses import asdict, dataclass
from math import isfinite

from config.settings import MarketSettings
from src.households import Household

TOLERANCE = 1e-9


@dataclass
class Offer:
    household_id: str
    group_id: int
    balance_kwh: float
    bid_eur_kwh: float
    ask_eur_kwh: float
    original_bid_eur_kwh: float | None = None
    original_ask_eur_kwh: float | None = None

    def __post_init__(self) -> None:
        if not all(isfinite(x) for x in (self.balance_kwh, self.bid_eur_kwh, self.ask_eur_kwh)):
            raise ValueError("Offers must have finite energy and prices.")
        if min(self.bid_eur_kwh, self.ask_eur_kwh) < 0:
            raise ValueError("Offers must have nonnegative prices.")
        if self.original_bid_eur_kwh is None:
            self.original_bid_eur_kwh = self.bid_eur_kwh
        if self.original_ask_eur_kwh is None:
            self.original_ask_eur_kwh = self.ask_eur_kwh


@dataclass(frozen=True)
class Transaction:
    transaction_id: str
    hour: int
    market: str
    seller_id: str
    buyer_id: str
    quantity_kwh: float
    price_eur_kwh: float
    reward_eur: float = 0.0

    @property
    def value_eur(self) -> float:
        return self.quantity_kwh * self.price_eur_kwh

    def as_dict(self) -> dict:
        return asdict(self)


def make_offer(household: Household, balance_kwh: float, reference_price: float,
               settings: MarketSettings) -> Offer:
    def clamp(price):
        return max(settings.minimum_offer_eur_kwh, min(settings.maximum_offer_eur_kwh, price))
    return Offer(household.household_id, household.group_id, balance_kwh,
                 clamp(reference_price * household.bid_multiplier),
                 clamp(reference_price * household.ask_multiplier))


def transfer_energy(buyer: Offer, seller: Offer, quantity_kwh: float) -> None:
    if not isfinite(quantity_kwh) or quantity_kwh <= 0:
        raise ValueError("Trading quantity must be finite and positive.")
    if buyer.household_id == seller.household_id:
        raise ValueError("Self-trades are forbidden.")
    if quantity_kwh > min(-buyer.balance_kwh, seller.balance_kwh) + TOLERANCE:
        raise ValueError("Trade exceeds available surplus or shortage.")
    buyer.balance_kwh += quantity_kwh
    seller.balance_kwh -= quantity_kwh
