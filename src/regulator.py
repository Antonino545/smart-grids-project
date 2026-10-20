"""Funded P2P rewards; end-of-hour grid fees can only finance later hours."""

from dataclasses import asdict, dataclass
from math import isfinite

from config.settings import MarketSettings, RegulatorSettings
from src.external_grid import GRID_ACCOUNT
from src.ledger import Ledger, REGULATOR_ACCOUNT
from src.market import Offer, Transaction


@dataclass
class RewardReservation:
    reservation_id: str
    hour: int
    seller_id: str
    amount_eur: float
    status: str = "reserved"
    transaction_id: str = ""


class Regulator:
    def __init__(self, settings: RegulatorSettings | None = None):
        self.settings = settings or RegulatorSettings()
        self.funds_eur = self.settings.initial_budget_eur
        self.reward_rate_eur_kwh = 0.0
        self.reservations: list[RewardReservation] = []
        self.history: list[dict] = []
        self._closed = True
        self._hour = -1
        self._opening = self.funds_eur
        self._hour_rewards = 0.0

    @property
    def available_eur(self) -> float:
        return self.funds_eur - sum(r.amount_eur for r in self.reservations if r.status == "reserved")

    def begin_hour(self, hour: int) -> None:
        if not self._closed:
            raise ValueError("Close the current regulator hour before starting another.")
        if any(r.status == "reserved" for r in self.reservations):
            raise ValueError("Unsettled reward reservation at hour boundary.")
        if hour != self._hour + 1:
            raise ValueError("Regulator hours must be consecutive.")
        self._closed = False
        self._hour, self._opening, self._hour_rewards = hour, self.funds_eur, 0.0
        s = self.settings
        self.reward_rate_eur_kwh = (
            s.upper_reward_eur_kwh if self._opening >= s.upper_tier_budget_eur else
            s.lower_reward_eur_kwh if self._opening >= s.lower_tier_budget_eur else 0.0)

    def guide(self, offers: list[Offer], reference_prices: dict[str, float], market: MarketSettings) -> None:
        s = self.settings
        for offer in offers:
            reference = reference_prices[offer.household_id]
            def guided(original, multiplier):
                value = (1 - s.guidance_strength) * original + s.guidance_strength * reference * multiplier
                return max(market.minimum_offer_eur_kwh, min(market.maximum_offer_eur_kwh, value))
            offer.bid_eur_kwh = guided(offer.original_bid_eur_kwh, s.guided_bid_multiplier)
            # Leave enough headroom that a funded discount cannot breach the minimum price.
            offer.ask_eur_kwh = max(
                market.minimum_offer_eur_kwh + s.reward_discount_fraction * self.reward_rate_eur_kwh,
                guided(offer.original_ask_eur_kwh, s.guided_ask_multiplier))
            if offer.ask_eur_kwh > market.maximum_offer_eur_kwh:
                raise ValueError("Price limits cannot accommodate the configured reward discount.")

    def quote(self, buyer: Offer, seller: Offer, quantity_kwh: float):
        if self._closed or not isfinite(quantity_kwh) or quantity_kwh <= 0:
            raise ValueError("Reward quote quantity must be positive.")
        rate = self.reward_rate_eur_kwh
        reward = quantity_kwh * rate
        if rate == 0:
            return buyer.bid_eur_kwh, seller.ask_eur_kwh, 0.0, None
        if reward > self.available_eur:
            # No unfunded discount or partial guarantee: try the original offers.
            return buyer.original_bid_eur_kwh, seller.original_ask_eur_kwh, 0.0, None
        reservation = RewardReservation(f"reward-{len(self.reservations):06d}", self._hour,
                                        seller.household_id, reward)
        self.reservations.append(reservation)
        price = seller.ask_eur_kwh - self.settings.reward_discount_fraction * rate
        return buyer.bid_eur_kwh, price, reward, reservation.reservation_id

    def _reservation(self, reservation_id: str) -> RewardReservation:
        record = next(r for r in self.reservations if r.reservation_id == reservation_id)
        if record.status != "reserved":
            raise ValueError("Reward reservation was already settled.")
        return record

    def release(self, reservation_id: str) -> None:
        self._reservation(reservation_id).status = "released"

    def pay(self, reservation_id: str, transaction_id: str) -> None:
        reservation = self._reservation(reservation_id)
        if reservation.amount_eur > self.funds_eur:
            raise ValueError("Unfunded reward payment.")
        self.funds_eur -= reservation.amount_eur
        self._hour_rewards += reservation.amount_eur
        reservation.status, reservation.transaction_id = "paid", transaction_id

    def end_hour(self, grid_trades: list[Transaction], ledger: Ledger) -> None:
        if self._closed:
            raise ValueError("Regulator hour is already closed.")
        if any(r.status == "reserved" for r in self.reservations):
            raise ValueError("Cannot close hour with reserved rewards.")
        fees = 0.0
        for transaction in grid_trades:
            if transaction.market != "grid" or transaction.hour != self._hour:
                raise ValueError("Fees require current-hour external-grid transactions.")
            household = transaction.seller_id if transaction.buyer_id == GRID_ACCOUNT else transaction.buyer_id
            fee = transaction.quantity_kwh * self.settings.grid_fee_eur_kwh
            ledger.transfer(self._hour, "grid_fee", household, REGULATOR_ACCOUNT, fee, transaction.transaction_id)
            fees += fee
        self.funds_eur += fees
        self._closed = True
        self.history.append({"hour": self._hour, "opening_funds_eur": self._opening,
                             "reward_rate_eur_kwh": self.reward_rate_eur_kwh,
                             "reward_paid_eur": self._hour_rewards, "grid_fees_eur": fees,
                             "closing_funds_eur": self.funds_eur})

    def reservation_records(self) -> list[dict]:
        return [asdict(r) for r in self.reservations]
