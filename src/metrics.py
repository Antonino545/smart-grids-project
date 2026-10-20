"""Auditable KPI definitions with explicit denominators and cash-account boundaries."""

from src.external_grid import GRID_ACCOUNT
from src.simulator import SimulationResult


def calculate_metrics(result: SimulationResult) -> dict:
    def volume(market):
        return sum(t.quantity_kwh for t in result.transactions if t.market == market)
    p2p = volume("p2p")
    imports = sum(t.quantity_kwh for t in result.transactions if t.market == "grid" and t.seller_id == GRID_ACCOUNT)
    exports = sum(t.quantity_kwh for t in result.transactions if t.market == "grid" and t.buyer_id == GRID_ACCOUNT)
    accounts = sorted({b.household_id for b in result.balances})
    household_cost = -sum(result.ledger.balance(account) for account in accounts)
    grid_net_cost = result.ledger.balance(GRID_ACCOUNT)
    fees = sum(m.amount_eur for m in result.ledger.movements if m.kind == "grid_fee")
    rewards = sum(m.amount_eur for m in result.ledger.movements if m.kind == "reward")
    initial_fund = result.regulator.settings.initial_budget_eur if result.regulator else 0.0
    closing_fund = result.regulator.funds_eur if result.regulator else 0.0
    first_hour, last_hour = min(b.hour for b in result.balances), max(b.hour for b in result.balances)
    initial_storage = sum(b.stored_start_kwh for b in result.balances if b.hour == first_hour)
    final_storage = sum(b.stored_end_kwh for b in result.balances if b.hour == last_hour)
    pv = sum(b.pv_kwh for b in result.balances)
    demand = sum(b.demand_kwh for b in result.balances)
    losses = sum(b.battery_loss_kwh for b in result.balances)
    energy_error = pv + imports + initial_storage - demand - exports - final_storage - losses
    money_error = household_cost - (grid_net_cost + fees - rewards)
    if abs(energy_error) > 1e-7 or abs(money_error) > 1e-7:
        raise ValueError("Community energy or financial reconciliation failed.")
    return {
        "p2p_share_pct": 100 * p2p / result.surplus_available_kwh if result.surplus_available_kwh > 1e-9 else None,
        "p2p_energy_kwh": p2p,
        "surplus_available_after_self_balancing_kwh": result.surplus_available_kwh,
        "pv_surplus_before_battery_charging_kwh": sum(b.pv_surplus_before_charging_kwh for b in result.balances),
        "p2p_to_grid_exports_ratio": p2p / exports if exports > 1e-9 else None,
        "p2p_transaction_count": sum(t.market == "p2p" for t in result.transactions),
        "aggregator_energy_kwh": volume("aggregator"),
        "grid_imports_kwh": imports, "grid_exports_kwh": exports,
        "household_net_cost_eur": household_cost,
        "external_grid_net_cost_eur": grid_net_cost,
        "community_including_regulator_net_cost_eur": household_cost - (closing_fund - initial_fund),
        "regulator_fee_revenue_eur": fees, "regulator_reward_expenditure_eur": rewards,
        "regulator_initial_funds_eur": initial_fund, "regulator_remaining_funds_eur": closing_fund,
        "battery_charge_kwh": sum(b.charge_kwh for b in result.balances),
        "battery_discharge_kwh": sum(b.discharge_kwh for b in result.balances),
        "battery_loss_kwh": losses, "battery_initial_stored_kwh": initial_storage,
        "battery_final_stored_kwh": final_storage,
        "active_battery_count": len({b.household_id for b in result.balances if b.soc is not None}),
        "pv_generation_kwh": pv, "demand_kwh": demand,
        "energy_reconciliation_error_kwh": energy_error,
        "financial_reconciliation_error_eur": money_error,
        "block_count": len(result.blockchain.blocks) if result.blockchain else 0,
        "blockchain_valid": result.blockchain.validate(result.transactions, last_hour + 1) if result.blockchain else None,
    }
