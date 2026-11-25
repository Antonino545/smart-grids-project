# Smart Grids — Prosumer Community Simulator

A reproducible Python simulator for 150 aggregate building meters: 100 PV-equipped
prosumers (55 battery owners) plus 50 consumer-only buildings. Each of 10 mixed
neighborhoods contains 10 prosumers and 5 consumers. It implements self-balancing, neighborhood P2P trading,
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

# Add the regulator policy variants G-K (variants of B, see below):
python main.py --include-priority --include-policy

# Full report run: A-L, fixed demand versus PV-aware demand shifting:
python main.py --include-priority --include-policy --include-combined --compare-demand-response

# Run one regulated scenario, or skip charts:
python main.py --scenario B --output results/single_B
python main.py --scenario all --no-charts --output results/numerical_run

# Override defaults using a JSON configuration:
python main.py --config config/default.json --include-priority

# Reproduce the original 100-prosumer community, without the 50 additions:
python main.py --config config/mixed_100_baseline.json --include-priority --output results/baseline_100
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
### Regulator policy variants (G-K)

`--include-policy` adds five copies of B (55 batteries, regulated, self-consumption
first), each with **one** regulator rule changed. Their settings are in
`src/experiments.py` (`REGULATOR_OVERRIDES`) and are saved in each scenario's
`summary.json`.

| Scenario | Change from B | Setting |
|---|---|---|
| G | Lower fee: EUR 0.0025/kWh instead of 0.01 | `grid_fee_eur_kwh` |
| H | Bigger reward: EUR 0.075/kWh (0.0375 lower tier) instead of 0.02 | `upper_/lower_reward_eur_kwh` |
| I | Fee only on grid energy a same-group neighbour could have traded that hour | `fee_scope: "missed_local"` |
| J | Whole fund returned at day end, split by each meter's P2P kWh | `refund_leftover: true` |
| K | Hourly reward = fund / possible P2P kWh, capped at EUR 0.10/kWh | `reward_mode: "budget_sized"` |

Why: in B the fee hits every grid kWh, day and night (about 18,000 kWh), while
the reward only reaches P2P kWh (about 2,060), so most fees stay in the fund.
On the default day, G's smaller fee leaves too little money for afternoon
rewards, so it trades less than B; H and K trade more, and K, which sizes each
hour's reward to the money in the fund (high in the morning, lower after the fund
is spent around midday), trades the most. J trades like B but returns the fund. When a
reward cannot be funded, the trade keeps the guided prices and only loses the
reward. The same switches can be set for any run in the `regulator` section of a JSON config.

### Combined scenario L (F + K)

`--include-combined` adds **L**: F's settlement order (regulated, owner PV offered
to neighbours before any battery charging) with K's reward rule
(`reward_mode: "budget_sized"`). Nothing else changes, and no parameter was tuned.
Each hour the reward rate is

    r_h = min(r_max, A_h / P_h),   P_h = sum over groups of min(group surplus, group shortage)

where `A_h` is the fund available at the start of the hour (fees from earlier hours
minus rewards paid) and `r_max` is `max_reward_eur_kwh` (EUR 0.10/kWh). Sellers
discount their ask by `r_h / 2` and receive `r_h` per kWh from the fund, only when
the full reward is already held. Fees (EUR 0.01 per grid kWh) are added after the hour.

```bash
# Full comparison including L, with and without demand response:
python main.py --include-priority --include-policy --include-combined --compare-demand-response

# L alone:
python main.py --scenario L --output results/single_L

# Robustness: A, B, D, F, K, L on 20 seeds (42-61), fixed demand and demand response (~7 min):
python scripts/robustness.py
python scripts/robustness.py --seeds 1 2 3 4 5 6 7 8 9 10 --output results/robustness_alt
```

The robustness script writes `results/robustness/runs.csv` (one row per seed, condition
and scenario), `summary.csv` (mean, sample standard deviation, min, max),
`l_win_rates.csv` (share of seeds in which L beats F and K for each KPI) and
`robustness.png/svg`. Inside each seed and condition all scenarios share one input hash.
"Storage-adjusted" cost subtracts the change in stored energy valued at
import tariff x discharge efficiency (EUR 0.285/kWh).

Recorded result (default day, seed 42, fixed demand): L trades 2,712 kWh P2P against
F's 2,682 and K's 2,254; meters + regulator cost EUR 4,743.53 (F 4,753.21, K 4,795.67).
With demand response L trades 2,629 kWh against F's 2,589. Over 20 seeds (paired
differences, mean ± sd across seeds, share of seeds in which L is better):

| L minus | Condition | P2P kWh | Meter cost EUR | Storage-adjusted meters + regulator EUR |
|---|---|---:|---:|---:|
| F | fixed | +52 ± 102 (75%) | -79.6 ± 29.8 (100%) | -16.9 ± 19.6 (85%) |
| F | demand response | +65 ± 96 (80%) | -83.5 ± 28.3 (100%) | -19.2 ± 18.1 (85%) |
| K | fixed | +486 ± 86 (100%) | -51.4 ± 15.4 (100%) | -7.6 ± 11.2 (70%) |
| K | demand response | +490 ± 95 (100%) | -51.1 ± 16.8 (100%) | -6.7 ± 11.1 (70%) |

L clearly beats K in P2P, because F's battery order leaves more PV for neighbours.
Against F, L is slightly cheaper for the community (about EUR 17-19/day, 0.4% of the
bill, beyond two standard errors of the paired mean) and trades slightly more P2P.
The gain is small because K's rule spends the whole fund in the current hour: under
P2P-first ordering the fund runs low before the midday peak, where L pays less than
F's fixed EUR 0.02/kWh; L wins it back in the morning and late afternoon. Most of L's
lower meter cost is reward money moved from the regulator to the meters. The report
therefore recommends L, with F as a simpler fallback. Pages 27-31 explain this and
list the best scenario for each objective. Pages 32-33 are a presentation summary: a
headline chart and table for A, B, F and L, the average daily cost per building type
and per participant group, the share of meters paying less than in A, and five key
messages for the slides.

These results changed when house PV was resized to typical Italian systems (mean about
4 kWp instead of 6.3), synthetic clouds were made daily instead of hourly, and P2P
buyers were made to take the cheapest seller first: with the earlier, larger house PV
and random seller order, L and F were economically indistinguishable.

Each hour has a deterministic matching stream, separate from community and data
generation. Same inputs, seed, code and environment reproduce the transaction
journal and block hashes. Stochastic results can change with another seed.

## Building types and dynamic loads

The original **100 prosumer buildings** remain: 50 small houses,
30 apartment blocks, 10 supermarkets and 10 schools. The 50 new consumers add
25 houses, 15 blocks, 5 supermarkets and 5 schools, with zero PV and no batteries.
Every group retains its original 5/3/1/1 prosumers and receives five consumers.
Consumer types are shuffled across groups; every neighborhood contains both roles.
Every block has one roof
and aggregates the consumption of all its flats. Roof area limits PV; floors and
flat count increase residential demand without multiplying roof area.

Houses/blocks have morning and evening peaks. Supermarkets have a persistent base
load plus opening-hour activity. Schools have weekday daytime loads and reduced
weekend operation. All types have seeded building-specific values and daily
variation. Battery capacity/power is also configurable by type, with exactly 55
owners. These are **synthetic, configurable engineering defaults**. See
[the building model](docs/building_model.md) for values, equations and limitations.

Technical CSV/config names such as `household_id` and `household_count` remain for
compatibility. `simulation.household_count` counts the original prosumers;
`buildings.consumer_count` counts additions. Total meters are their sum.
The default JSON is loaded first, then partial overrides are merged recursively.
The library generator alone retains a zero-addition default unless supplied building settings.
`comparison.json`
explicitly records this unit and the number of homes (flats and houses) it contains.

## Community map

`results/charts/community_map.png` (also SVG) shows the actual community as a
10-row x 15-column schematic by default. Each row is one neighborhood: H001-H010
belong to G1, H011-H020 to G2, and so on, with H101-H150 distributed five per group.
Display columns are shuffled, mixing both roles within each row.
Blue buildings have PV plus a battery (B badge); gold buildings have PV only;
pale green buildings labeled CONSUMER have neither PV nor batteries. HOUSE/BLOCK/SHOP/SCHOOL markers
show the type, meter ID, PV capacity and block floor count. Seeded battery assignment gives
five or six owners per neighborhood, totaling 55 owners, 45 PV-only prosumers and 50 consumers.
The map is generated from the same household objects used by the simulation.
`charts/data/community_layout.csv` exports cell assignments and attributes;
`charts/data/neighborhood_distribution.csv` exports group totals.

The row/column positions are for display only. There are no geographic coordinates,
road distances, electrical feeder geometry or distance-based restrictions in this
model. Membership defines eligible P2P partners, regardless of positions on this
schematic. The layout does not change ownership or the simulation results. Other
configured group sizes render as one row per group and may not form a square.
Regenerate with `python main.py --include-priority --include-policy --include-combined` (unless `--no-charts` is used).

## Configuration

`config/buildings.py` configures type shares, geometry and load archetypes.
`config/settings.py` contains frozen, validated dataclasses. `config/default.json`
contains their complete default values. Supply a partial JSON object to override
only the fields needed:

```json
{
  "simulation": {"random_seed": 123, "hours": 24},
  "buildings": {"types": {"school": {"weekend_multiplier": 0.1}}},
  "market": {"grid_import_tariff_eur_kwh": 0.30},
  "regulator": {"guidance_strength": 0.65}
}
```

Supported sections are `simulation`, `households`, `forecast`, `market`,
`regulator`, `blockchain`, and `buildings`. Unknown fields/sections and invalid values fail
with an error. `simulation.battery` holds nested battery specifications. Equal
neighborhood sizes are required. Duration is configurable in hourly steps;
non-hourly time steps are explicitly rejected by this first hourly input model.
All prices are EUR/kWh, quantities kWh, power kW and SOC a fraction of capacity.

## Inputs and forecasting

**The shipped experiment uses synthetic data, not real measurements.** No
historical datasets were supplied. Synthetic weather, synthetic household demand
and synthetic price history each have explicit source labels in every input row.
The area is **Turin (Torino)**, 45.07 N 7.69 E. The default day is 15 June 2026
with a fixed UTC+02:00 offset. Weather is synthetic but calibrated to JRC PVGIS
data for Turin; it is not a forecast for that specific date.

Each hour, the sun position over Turin and the clear-sky light on every panel are
computed from the panel tilt (houses 20°, blocks/schools 15°, supermarkets 10°,
all facing south). A seeded cloud factor (one per day, 0.65–1.0, with at most ±0.05 change from hour to hour) scales the light. PV energy =
installed kW × panel light / 1000 × 0.75 × step hours, capped at installed
capacity. This gives about 4.9 kWh per kW per day in June, as PVGIS does for
Turin. See `docs/building_model.md` for sources.
Demand depends on building type, size, residential units or floor area, opening
hours, weekdays/weekends and seeded daily variation. See the building-model guide.
School holidays and weather-sensitive HVAC demand are not modeled.
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

The original brief described 100 households. The accepted extension uses 100
prosumer meters plus 50 consumer meters while retaining 10 equal groups, 55 battery owners,
24 hourly steps, funded P2P rewards and 10 miners with `000` hashes. Building-type
composition and sizing are modeling assumptions, configurable for sensitivity tests.
Suggested battery values and the following behavioral defaults are engineering
choices, not separately verified professor requirements.

- Battery defaults: 10 kWh, 3 kW charge/discharge, 95% efficiency each way,
  initial SOC 20%, allowed SOC 10–90%. Type scales of 1/4/10/6 for house/block/shop/school
  multiply both base capacity and power; these are engineering defaults.
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
- Neighborhood buyers take turns in seeded random order. Each buyer buys from the
  cheapest seller in its group first, then the next cheapest, until its need is met
  or the next ask is above its bid (simple price sorting, as suggested in the brief).
  P2P pays the seller ask. The aggregator
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
  for the discount. Unfunded proposals keep the guided prices without a reward;
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

- `inputs/households.csv`: aggregate meter identities, building types, roof/floor
  geometry, home counts, panel tilt, groups, PV, ownership, type-specific battery specs,
  weekday/weekend profiles and offer parameters.
- `inputs/hourly_inputs.csv`: all building-hour records and source labels.
- `charts/building_type_profiles.png/.svg`: mean hourly demand and PV per building
  type, backed by `charts/data/building_type_hourly.csv` and `building_type_summary.csv`.
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
  Regenerate every chart with `python main.py --include-priority --include-policy --include-combined`.
- Each scenario folder contains `summary.json`, `household_hourly.csv`,
  `household_costs.csv`, `community_hourly.csv`, `transactions.csv`,
  `cash_ledger.csv`, `regulator_hourly.csv`, `reward_reservations.json`, and
  `blockchain.json`. `summary.json` records exact configuration and provenance.
- `blockchain.json` contains miners, attempts and all hourly blocks. The first
  block references 64 zero characters, without an extra genesis block. Miners
  take turns trying nonces; this is not a physical concurrent network or a
  cryptocurrency. A configurable attempt limit raises an error if mining fails.

## PDF report

`output/pdf/smart_grids_project_report.pdf` is the single project report. It
describes the mixed-building model and the actual results of scenarios A-L,
including the robustness analysis and the presentation summary (pages 32-33).
An editable LaTeX version can be exported on demand with
`python scripts/create_report.py --format latex --output <folder>/main.tex`.
After running the full report command and `python scripts/robustness.py`, rebuild the report with:

```bash
python -m pip install -r requirements-report.txt
python scripts/create_report.py
```

PDF dependencies are optional and do not affect running the simulator. The report
reads `results/comparison.json`, type summaries, chart images and the dated
validation record in `docs/current_validation.json`; a mismatching input hash is
explicitly flagged. The report builder targets the mixed-building six-scenario
experiment. Other compositions require reviewing any illustrative narrative
alongside the exported configuration.

The PDF includes a team parameter guide on pages 11–22: all 181 configuration
values, units, effects, building-type comparisons, worked examples and a partial
JSON experiment workflow. Values are read from the saved run configuration.
`scripts/report_parameters.py` checks that every configuration field is documented;
the report build fails if fields are added or removed without updating the guide.

Optional demand response shifts a bounded share of load toward each owner's PV
forecast, only for prosumers without batteries. Daily energy remains unchanged;
consumer-only meters and battery owners retain their loads. The default remains
fixed demand. Paired results go to `results/demand_response/`, with comparison
graphs and CSV/JSON in the parent output folder. When present, PDF pages 23–25
explain the behavior, hourly curves, results, a worked example and limitations.
See [the demand-response model](docs/demand_response.md) for settings and audits.

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
