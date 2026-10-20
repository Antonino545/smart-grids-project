"""Every cash movement has one payer and one payee (EUR, unrounded internally)."""

from dataclasses import asdict, dataclass
from math import isfinite

from src.market import Transaction

REGULATOR_ACCOUNT = "regulator"


@dataclass(frozen=True)
class CashMovement:
    movement_id: str
    hour: int
    kind: str
    payer: str
    payee: str
    amount_eur: float
    transaction_id: str


class Ledger:
    def __init__(self) -> None:
        self.movements: list[CashMovement] = []

    def transfer(self, hour: int, kind: str, payer: str, payee: str,
                 amount_eur: float, transaction_id: str) -> None:
        if not isfinite(amount_eur) or amount_eur < 0 or payer == payee:
            raise ValueError("Invalid cash transfer.")
        self.movements.append(CashMovement(
            f"cash-{len(self.movements):07d}", hour, kind, payer, payee, amount_eur, transaction_id))

    def record_trade(self, transaction: Transaction) -> None:
        self.transfer(transaction.hour, transaction.market, transaction.buyer_id,
                      transaction.seller_id, transaction.value_eur, transaction.transaction_id)
        if transaction.reward_eur:
            if transaction.market != "p2p":
                raise ValueError("Only P2P sales qualify for rewards.")
            self.transfer(transaction.hour, "reward", REGULATOR_ACCOUNT, transaction.seller_id,
                          transaction.reward_eur, transaction.transaction_id)

    def balance(self, account: str) -> float:
        return sum((m.amount_eur if m.payee == account else 0)
                   - (m.amount_eur if m.payer == account else 0) for m in self.movements)

    def verify(self) -> None:
        accounts = {m.payer for m in self.movements} | {m.payee for m in self.movements}
        if abs(sum(self.balance(account) for account in accounts)) > 1e-7:
            raise ValueError("Cash ledger does not conserve money.")

    def as_dicts(self) -> list[dict]:
        return [asdict(movement) for movement in self.movements]
