"""Funded P2P rewards; end-of-hour grid fees can only finance later hours."""

from collections import defaultdict
from dataclasses import asdict, dataclass
from math import isfinite

from config.settings import MarketSettings, RegulatorSettings
from src.external_grid import GRID_ACCOUNT
from src.ledger import Ledger, REGULATOR_ACCOUNT
from src.market import Offer, TOLERANCE, Transaction


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
        self._day_p2p_kwh: dict[str, float] = defaultdict(float)

    @property
    def available_eur(self) -> float:
        return self.funds_eur - sum(r.amount_eur for r in self.reservations if r.status == "reserved")

    def begin_hour(self, hour: int, offers: list[Offer] | None = None) -> None:
        if not self._closed:
            raise ValueError("Close the current regulator hour before starting another.")
        if any(r.status == "reserved" for r in self.reservations):
            raise ValueError("Unsettled reward reservation at hour boundary.")
        if hour != self._hour + 1:
            raise ValueError("Regulator hours must be consecutive.")
        self._closed = False
        self._hour, self._opening, self._hour_rewards = hour, self.funds_eur, 0.0
        s = self.settings
        if s.reward_mode == "budget_sized":
            # Spend the fund on the P2P energy that is possible this hour: within each group,
            # at most min(total surplus, total shortage) can change hands.
            if offers is None:
                raise ValueError("Budget-sized rewards need this hour's offers.")
            surplus, shortage = defaultdict(float), defaultdict(float)
            for offer in offers:
                if offer.balance_kwh > TOLERANCE:
                    surplus[offer.group_id] += offer.balance_kwh
                elif offer.balance_kwh < -TOLERANCE:
                    shortage[offer.group_id] -= offer.balance_kwh
            possible = sum(min(surplus[g], shortage[g]) for g in surplus)
            self.reward_rate_eur_kwh = (min(s.max_reward_eur_kwh, self.available_eur / possible)
                                        if possible > TOLERANCE else 0.0)
        else:
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
            # No unfunded discount or partial guarantee. The guided prices still apply:
            # guidance costs the fund nothing, so an empty fund only removes the reward.
            return buyer.bid_eur_kwh, seller.ask_eur_kwh, 0.0, None
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

    def end_hour(self, trades: list[Transaction], ledger: Ledger,
                 group_of: dict[str, int] | None = None, day_end: bool = False) -> None:
        """Charge grid fees, then (optionally) refund the fund at the end of the day.

        ``trades`` may contain every market; only current-hour grid trades pay fees.
        ``group_of`` maps meter IDs to neighbourhoods and is required for "missed_local".
        """
        if self._closed:
            raise ValueError("Regulator hour is already closed.")
        if any(r.status == "reserved" for r in self.reservations):
            raise ValueError("Cannot close hour with reserved rewards.")
        if any(t.hour != self._hour for t in trades):
            raise ValueError("Fees require current-hour transactions.")
        grid_trades = [t for t in trades if t.market == "grid"]
        for trade in trades:
            if trade.market == "p2p":
                self._day_p2p_kwh[trade.seller_id] += trade.quantity_kwh
                self._day_p2p_kwh[trade.buyer_id] += trade.quantity_kwh
        chargeable = self._chargeable_fractions(grid_trades, group_of)
        fees = 0.0
        for transaction in grid_trades:
            household = transaction.seller_id if transaction.buyer_id == GRID_ACCOUNT else transaction.buyer_id
            fee = transaction.quantity_kwh * chargeable[transaction.transaction_id] * self.settings.grid_fee_eur_kwh
            if fee > 0:
                ledger.transfer(self._hour, "grid_fee", household, REGULATOR_ACCOUNT, fee, transaction.transaction_id)
            fees += fee
        self.funds_eur += fees
        refunds = self._refund(ledger) if day_end and self.settings.refund_leftover else 0.0
        if day_end:
            self._day_p2p_kwh = defaultdict(float)
        self._closed = True
        self.history.append({"hour": self._hour, "opening_funds_eur": self._opening,
                             "reward_rate_eur_kwh": self.reward_rate_eur_kwh,
                             "reward_paid_eur": self._hour_rewards, "grid_fees_eur": fees,
                             "refund_eur": refunds, "closing_funds_eur": self.funds_eur})

    def _chargeable_fractions(self, grid_trades: list[Transaction],
                              group_of: dict[str, int] | None) -> dict[str, float]:
        """Share of each grid trade that pays the fee (1.0 for every trade under "all_grid")."""
        if self.settings.fee_scope == "all_grid":
            return {t.transaction_id: 1.0 for t in grid_trades}
        if group_of is None:
            raise ValueError("A missed_local fee needs each meter's group.")
        imports, exports = defaultdict(float), defaultdict(float)
        for t in grid_trades:
            if t.buyer_id == GRID_ACCOUNT:
                exports[group_of[t.seller_id]] += t.quantity_kwh
            else:
                imports[group_of[t.buyer_id]] += t.quantity_kwh
        fractions = {}
        for t in grid_trades:
            exporting = t.buyer_id == GRID_ACCOUNT
            group = group_of[t.seller_id if exporting else t.buyer_id]
            # Energy one neighbour sent to the grid while another bought from it could have
            # stayed local: min(imports, exports) per group, shared pro rata on both sides.
            missed = min(imports[group], exports[group])
            own_side = exports[group] if exporting else imports[group]
            fractions[t.transaction_id] = missed / own_side if own_side > TOLERANCE else 0.0
        return fractions

    def _refund(self, ledger: Ledger) -> float:
        """Return the whole fund to the day's P2P traders, in proportion to their P2P kWh."""
        total = sum(self._day_p2p_kwh.values())
        available = self.available_eur
        if total <= TOLERANCE or available <= 0:
            return 0.0
        paid = 0.0
        meters = sorted(self._day_p2p_kwh)
        for index, meter in enumerate(meters):
            amount = (available - paid if index == len(meters) - 1
                      else available * self._day_p2p_kwh[meter] / total)
            amount = max(0.0, min(amount, available - paid))
            if amount > 0:
                ledger.transfer(self._hour, "refund", REGULATOR_ACCOUNT, meter, amount, f"refund-{self._hour:03d}")
                paid += amount
        self.funds_eur -= paid
        return paid

    def reservation_records(self) -> list[dict]:
        return [asdict(r) for r in self.reservations]
