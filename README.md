# Smart Grids — Prosumer Community Simulator

A reproducible Python simulator for 100 PV-equipped households in 10 neighborhoods,
including 55 battery owners. It implements self-balancing, neighborhood P2P trading,
a community aggregator, external-grid settlement, funded regulation and an hourly
Proof-of-Work blockchain. Implementation follows the supplied plan in tested stages.
Presentation preparation and ZIP packaging are deferred at the user's request.

## Install and run

Python **3.11 or later** is required. The recorded verification used Python 3.14.7.
Run from this project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
python main.py
```

`python main.py` runs scenarios A–D, mines all hourly blocks, checks energy and
cash conservation, and writes CSV/JSON outputs and PNG/SVG charts to `results/`.
The first matplotlib run may take longer while its font cache is built.
No network service, GPU, blockchain account, or web interface is required.

```bash
# Include the optional alternative battery strategy, scenarios E and F:
python main.py --include-priority

# Run one regulated scenario, or skip charts:
python main.py --scenario B --output results/single_B
python main.py --scenario all --no-charts --output results/numerical_run

# Override defaults using a JSON configuration:
python main.py --config config/default.json --include-priority
```

Use a separate output directory for each different configuration. The selected
scenario folders and comparison files are replaced on rerun; unselected scenario
folders in that directory are retained. Read `comparison.json` for the scenarios
belonging to the current comparison. Use `python scripts/verify_results.py` to independently verify the exported files.

`requirements.txt` declares compatible dependency ranges. `requirements-lock.txt`
records the exact packages installed on the verified Python/macOS environment;
use the ranged file on other Python versions/platforms because some pinned
versions may require a newer interpreter. For reproducibility on the same
platform, install with `python -m pip install -r requirements-lock.txt`.

## Scenarios

| Scenario | Battery operation | Regulation | Charging priority |
|---|---|---|---|
| A | 55 owners | Off | Self-consumption first |
| B | 55 owners | On | Self-consumption first |
| C | Disabled | Off | Counterfactual |
| D | Disabled | On | Counterfactual |
| E | 55 owners | Off | P2P before charging |
| F | 55 owners | On | P2P before charging |

The community and input data are generated **once**, then reused without mutation.
C/D disable battery operation while retaining original ownership metadata. E/F
are optional. Scenario definitions explicitly select their strategy; they override
the default `simulation.battery.strategy` used by the standalone engine API.
Each hour has a deterministic matching stream, separate from community and data
generation. Same inputs, seed, code and environment reproduce the transaction
journal and block hashes. Stochastic results can change with another seed.

## Configuration

`config/settings.py` contains frozen, validated dataclasses. `config/default.json`
contains their complete default values. Supply a partial JSON object to override
only the fields needed:

```json
{
  "simulation": {"random_seed": 123, "hours": 24},
  "households": {"pv_capacity_min_kw": 2.0, "pv_capacity_max_kw": 6.0},
  "market": {"grid_import_tariff_eur_kwh": 0.30},
  "regulator": {"guidance_strength": 0.65}
}
```

Supported sections are `simulation`, `households`, `forecast`, `market`,
`regulator`, and `blockchain`. Unknown fields/sections and invalid values fail
with an error. `simulation.battery` holds nested battery specifications. Equal
neighborhood sizes are required. Duration is configurable in hourly steps;
non-hourly time steps are explicitly rejected by this first hourly input model.
All prices are EUR/kWh, quantities kWh, power kW and SOC a fraction of capacity.

## Inputs and forecasting

**The shipped experiment uses synthetic data, not real measurements.** No
historical datasets were supplied. Synthetic weather, synthetic household demand
and synthetic price history each have explicit source labels in every input row.
The default day is 15 June 2026 with a fixed UTC+02:00 offset, chosen to demonstrate
a sunny summer profile; it is not a weather claim about that date or location.

PV energy = installed kW × irradiance / 1000 × performance factor × step hours,
capped at installed capacity × step hours. Synthetic irradiance follows a daylight
curve with seeded cloud factors. Configured sunrise/sunset determine nighttime.
Demand combines a base load with morning/evening peaks, household shifts and
seeded profile variation. The same daily profile repeats on longer runs.
Reference prices are averages of **only pre-start historical observations** for
each hour of day. The default 14-day price history is synthetic. At least one
pre-start observation for every hour of day is required; future observations
cannot affect forecasts.

To use real data, supply `forecast.weather_csv`, `forecast.demand_csv`, and/or
`forecast.historical_prices_csv`. Mixed real/synthetic inputs keep separate source
labels. See [input formats](docs/input_formats.md) for columns, units, coverage and
forecast provenance requirements. This version does not automatically download
or calibrate historical datasets. Timestamps include a UTC offset; use one
consistent fixed offset per experiment. Seasonal daylight and named-zone DST
calendars are not inferred automatically.

## Battery and market assumptions

Confirmed design values from the supplied brief are 100 households, 10 equal
groups, 55 battery owners, 24 initial hourly steps, funded P2P rewards and 10
simulated miners with `000` hashes. They are configurable for sensitivity tests.
Suggested battery values and the following behavioral defaults are engineering
choices, not separately verified professor requirements.

- Battery defaults: 10 kWh, 3 kW charge/discharge, 95% efficiency each way,
  initial SOC 20%, allowed SOC 10–90%. Owners receive specifications individually.
- Stored energy changes by `charge × efficiency − discharge / efficiency`.
  Charge/discharge columns are measured on the household AC side. Losses are
  exported separately. Charging uses only the owner's remaining PV; discharge
  only covers the owner's current demand. No simultaneous charge/discharge,
  grid charging, P2P charging, or stored-energy sales are allowed.
- In A/B, surplus charges before P2P. In E/F, surplus is offered to P2P first,
  then unsold owner PV charges before the aggregator. Initial battery energy is
  an exogenous inventory. Compare final inventory as well as electricity costs.
- Original offers multiply the reference forecast by each household's fixed
  bid/ask parameter, clipped to configurable limits. Default offer bounds are
  EUR 0.06–0.30/kWh, equal to external export/import tariffs. Negative historical
  reference prices are valid inputs but behavioral offers remain within bounds.
- Neighborhood buyers and their seller encounter orders are shuffled. Every
  buyer can try every seller in its group. P2P pays the seller ask. The aggregator
  sorts ascending asks and descending bids, with household ID as a tie-breaker,
  and pays the midpoint. Remaining balances settle with the grid.
- The regulator blends original offers toward `1.04 × reference` for bids and
  `0.96 × reference` for asks, with default guidance strength 0.65. Guidance
  affects P2P only; the aggregator uses original offers. This fixed heuristic
  encourages compatible offers and is not a global optimization guarantee.
- Opening funds below EUR 1 give no reward; EUR 1 to below EUR 5 give EUR 0.01/kWh;
  EUR 5 or above give EUR 0.02/kWh. The tier stays fixed for the hour. A full
  reward for the proposed feasible quantity must be reserved before a discounted
  quote. The adjusted ask equals guided ask minus 50% of the rate; the seller
  receives trade payment plus the full reward. Guidance leaves price headroom
  for the discount. Unfunded proposals retry original offers without a reward;
  there are no partial-quantity subsidies. Rejected proposals release funds.
- Grid imports and exports each incur EUR 0.01/kWh when regulated. There are no
  internal-market fees. Fees enter the fund after settlement and become usable
  in the next hour. Initial fund is EUR 0. Only P2P sellers receive rewards.
- Household cash accounts may pay for electricity without a starting-cash limit.
  Every movement has a payer/payee. EUR calculations use floating point without
  per-trade cent rounding, with conservation checks at numerical tolerance.
- Batteries have no capital/degradation cost in this version. The model excludes
  power flow, feeder constraints, tax, strategic learning and physical networking.
  The blockchain logs trades independently and does not set quantities or prices.

## KPIs and accounting

Primary KPI: `100 × P2P kWh / surplus available after self-balancing`.
A zero denominator is JSON `null`, not a fabricated zero. For P2P-priority charging,
the denominator is surplus offered before P2P and before deferred charging.
Always compare P2P kWh and **PV surplus before battery charging** alongside shares.
`p2p_to_grid_exports_ratio` is dimensionless and is also null for zero exports.

Household net cost is purchases minus sale revenue, plus fees minus rewards.
Internal P2P/aggregator payments cancel when aggregated over households.
Household-plus-regulator net cost subtracts the change in regulator funds from
household cost and equals net external-grid payments. A growing regulator fund
therefore increases households' payments without constituting money destruction.
Initial/final battery inventory and all conversion losses are explicitly reported.
No monetary value is assigned to that inventory.

The simulator checks each household hourly:
`PV + battery discharge + purchases = demand + battery charge + sales`.
Storage changes reconcile with charging/discharging losses. Community totals obey
`PV + grid imports + initial stored = demand + grid exports + final stored + losses`.
Both household flows and full cash movements must reconcile before outputs pass.

## Output files

- `inputs/households.csv`: fixed identities, groups, PV, ownership, individual
  battery specs, demand profiles and offer parameters.
- `inputs/hourly_inputs.csv`: all household-hour records and source labels.
- `comparison.csv` / `comparison.json`: scenario KPIs and shared input hash.
- `discussion.md`: computed comparisons and limitations, without forced improvement.
- `charts/*.png` / `*.svg`: P2P, grid/aggregator, costs, fund, storage/surplus and SOC.
  Additional views show hourly PV/demand and P2P, surplus destinations, household
  cost distributions, regulation differences, battery flows and transaction prices.
  `charts/data/*.csv` contains the exact data behind these additional charts.
  Surplus destinations include deferred battery charging for E/F; their stacked
  totals equal the surplus offered before P2P. Regulation differences are shown
  only when both members of a scenario pair were run. Household box plots show
  medians/quartiles with 1.5-IQR whiskers. Transaction prices exclude rewards.
  Regenerate every chart with `python main.py --include-priority`.
- Each scenario folder contains `summary.json`, `household_hourly.csv`,
  `household_costs.csv`, `community_hourly.csv`, `transactions.csv`,
  `cash_ledger.csv`, `regulator_hourly.csv`, `reward_reservations.json`, and
  `blockchain.json`. `summary.json` records exact configuration and provenance.
- `blockchain.json` contains miners, attempts and all hourly blocks. The first
  block references 64 zero characters, without an extra genesis block. Miners
  take turns trying nonces; this is not a physical concurrent network or a
  cryptocurrency. A configurable attempt limit raises an error if mining fails.

## Tests and project structure

`python -m pytest -q` checks household composition, forecasting and cutoff rules,
battery constraints and conservation, both markets, grid settlement, fee/reward
funding, blockchain tampering/coverage, KPI calculations, scenario consistency,
exports and command-line execution. Tests create temporary outputs.

`config/` holds parameter models; `src/` holds one module per simulation concern;
`tests/` verifies behavior; `data/` reserves raw/processed datasets; `results/`
holds actual runs; `docs/` explains formats and validation; `scripts/` independently
verifies exported results. `main.py` is the command-line entry point. No placeholder
simulation modules remain.

## Submission

The supplied brief specifies ZIP submission by **8 January 2027**, with a live
presentation after the Christmas break on a date to be confirmed by the professor.
Runnable source, dependencies, tests, configuration, documentation and current
results remain in the project folder. ZIP packaging and presentation work are
deferred. No submission is sent automatically. See `docs/validation.md` for the recorded execution and checks.
