"""Hourly simulation engine; components are added in validated development stages."""

from dataclasses import dataclass
from random import Random

from config.settings import BlockchainSettings, MarketSettings, RegulatorSettings, SimulationSettings
from src.aggregator import trade_aggregator
from src.balancing import BalanceResult, self_balance
from src.battery import BatteryState
from src.blockchain import Blockchain
from src.external_grid import settle_grid
from src.forecasting import HourlyInput
from src.households import Household
from src.ledger import Ledger
from src.market import Transaction, make_offer
from src.p2p_market import trade_p2p
from src.regulator import Regulator


@dataclass
class SimulationResult:
    name: str
    balances: list[BalanceResult]
    transactions: list[Transaction]
    ledger: Ledger
    surplus_available_kwh: float
    regulator: Regulator | None = None
    blockchain: Blockchain | None = None
    battery_strategy: str = "self_consumption_first"


def run_simulation(households: list[Household], inputs: list[HourlyInput],
                   settings: SimulationSettings, market: MarketSettings | None = None,
                   name: str = "A", batteries_enabled: bool = True,
                   regulation_enabled: bool = False, regulator_settings: RegulatorSettings | None = None,
                   blockchain_enabled: bool = True, blockchain_settings: BlockchainSettings | None = None,
                   battery_strategy: str | None = None) -> SimulationResult:
    market = market or MarketSettings()
    battery_strategy = battery_strategy or settings.battery.strategy
    if battery_strategy not in {"self_consumption_first", "p2p_priority"}:
        raise ValueError("Unknown battery strategy.")
    batteries = {h.household_id: BatteryState.initialize(h.battery)
                 for h in households if batteries_enabled and h.battery}
    lookup = {h.household_id: h for h in households}
    if len(lookup) != settings.household_count or len(inputs) != settings.household_count * settings.hours:
        raise ValueError("Community/input sizes do not match configuration.")
    indexed = {(row.hour, row.household_id): row for row in inputs}
    if len(indexed) != len(inputs):
        raise ValueError("Duplicate hourly input records.")
    ledger = Ledger()
    regulator = Regulator(regulator_settings) if regulation_enabled else None
    if regulator and regulator.settings.initial_budget_eur:
        ledger.transfer(-1, "initial_funding", "initial_funder", "regulator", regulator.settings.initial_budget_eur, "initial")
    blockchain = Blockchain(blockchain_settings) if blockchain_enabled else None
    all_balances, all_transactions = [], []
    surplus_available = 0.0
    for hour in range(settings.hours):
        balances = [self_balance(indexed[(hour, h.household_id)], batteries.get(h.household_id),
                                 settings.timestep_hours, defer_surplus_charging=battery_strategy == "p2p_priority")
                    for h in households]
        surplus_available += sum(max(0, b.balance_kwh) for b in balances)
        offers = [make_offer(lookup[b.household_id], b.balance_kwh,
                             indexed[(hour, b.household_id)].reference_price_eur_kwh, market) for b in balances]
        if regulator:
            regulator.begin_hour(hour)
            regulator.guide(offers, {h.household_id: indexed[(hour, h.household_id)].reference_price_eur_kwh
                                     for h in households}, market)
        # Independent hourly streams prevent scenario-specific trade counts changing later order.
        trades = trade_p2p(offers, hour, Random(settings.random_seed + 2000 + hour), regulator)
        if battery_strategy == "p2p_priority":
            # Only unsold owner PV can charge here; purchased energy never enters storage.
            for balance, offer in zip(balances, offers):
                battery = batteries.get(balance.household_id)
                if battery and offer.balance_kwh > 0:
                    flow = battery.operate(offer.balance_kwh, settings.timestep_hours)
                    offer.balance_kwh -= flow.charge_kwh
                    balance.balance_kwh -= flow.charge_kwh
                    balance.charge_kwh += flow.charge_kwh
                    balance.battery_loss_kwh += flow.loss_kwh
                    balance.stored_end_kwh, balance.soc = battery.stored_kwh, battery.soc
        # Guidance targets P2P only; aggregator offers revert to original parameters.
        for offer in offers:
            offer.bid_eur_kwh = offer.original_bid_eur_kwh
            offer.ask_eur_kwh = offer.original_ask_eur_kwh
        trades += trade_aggregator(offers, hour)
        trades += settle_grid(offers, hour, market)
        verify_hour(balances, trades)
        for transaction in trades:
            ledger.record_trade(transaction)
        if regulator:
            regulator.end_hour([t for t in trades if t.market == "grid"], ledger)
            if abs(ledger.balance("regulator") - regulator.funds_eur) > 1e-8:
                raise ValueError("Regulator fund disagrees with cash ledger.")
        if blockchain:
            blockchain.mine_hour(hour, balances[0].timestamp, [t for t in trades if t.market != "grid"])
            if not blockchain.validate(all_transactions + trades, hour + 1):
                raise ValueError("Hourly blockchain validation failed.")
        all_balances.extend(balances)
        all_transactions.extend(trades)
    ledger.verify()
    return SimulationResult(name, all_balances, all_transactions, ledger, surplus_available, regulator, blockchain, battery_strategy)


def verify_hour(balances: list[BalanceResult], trades: list[Transaction]) -> None:
    for balance in balances:
        balance.verify()
        bought = sum(t.quantity_kwh for t in trades if t.buyer_id == balance.household_id)
        sold = sum(t.quantity_kwh for t in trades if t.seller_id == balance.household_id)
        if abs(balance.balance_kwh + bought - sold) > 1e-8:
            raise ValueError(f"Unsettled energy for {balance.household_id}, hour {balance.hour}.")
    if any(t.quantity_kwh <= 0 for t in trades):
        raise ValueError("Nonpositive transaction quantity.")
