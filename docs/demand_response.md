# PV-aware demand shifting

This optional day-ahead experiment changes consumption timing for the original
45 prosumers without battery ownership. The 50 consumer-only buildings and 55
battery owners keep their original hourly demand. C/D disable battery operation
without broadening demand-response eligibility, so all A–F use the same shifted
input dataset within the shifted condition.

The fixed-demand model remains the default. Run both conditions with:

```bash
python main.py --include-priority --compare-demand-response
python scripts/verify_results.py results
python scripts/verify_results.py results/demand_response
```

Fixed outputs stay in `results/`; shifted outputs go into
`results/demand_response/`. To run only shifting in a separate folder:

```bash
python main.py --config config/demand_response.json --include-priority --output results/shift_only
```

## What can move

| Type | Maximum removable share per original hour | Source and target window |
|---|---:|---|
| Small house | 20% | 06:00 inclusive to 23:00 exclusive |
| Apartment block | 15% | 06:00–23:00 |
| Supermarket | 5% | 07:00–22:00 |
| School | 10% | 08:00–17:00 |

These are illustrative engineering assumptions, not measured flexibility. Actual
nonresidential opening/closing hours further restrict the windows. Closed
weekends do not shift; the school's default weekend closure is respected.

## Implemented heuristic

1. Work independently for each eligible meter and complete local calendar day.
   Partial days are untouched, so no energy is borrowed from missing hours.
2. Rank permitted source hours by forecast deficit, with clock-hour tie-breaking.
   Removable energy is `min(flexible_fraction * original_demand,
   max(0, original_demand - forecast_PV))`.
3. Search feasible hours on the same date within `max_shift_hours` (default 6)
   earlier or later. Prefer the largest remaining own-PV surplus, then clock hour.
4. Receiving headroom is the smaller of remaining PV surplus and remaining
   rebound allowance. The allowance defaults to 50% of that hour's original
   demand, so a zero-load hour cannot acquire an arbitrary new peak.
5. Subtract and add exactly the same quantity. Unplaceable flexible demand stays
   at its original hour. No demand is dropped, no new PV is created, no storage
   is introduced, and no purchase forecast is used to schedule own-PV demand.

For example, 10 kWh demand at 19:00 with zero PV and 20% flexibility permits
moving up to 2 kWh. At 13:00, demand 2 kWh and PV 10 kWh leave 8 kWh surplus,
but the rebound cap allows only 1 extra kWh. Moving 1 kWh gives demands 9 and
3 kWh respectively. Daily demand stays unchanged and direct PV use rises by
1 kWh. If no further destination fits, the other potential 1 kWh is not moved.

## Accounting, evidence and limits

The scheduler reads forecast inputs before market settlement, never actual future
observations. Supplied demand CSVs are treated as baseline forecasts when enabled;
the code cannot validate whether a source was truly available at issuance.
The shifted folder preserves `inputs/hourly_inputs_baseline.csv`, final
`hourly_inputs.csv`, and a transfer journal `inputs/demand_shifts.csv`.

Paired CSV/JSON summaries are saved as `results/demand_response_comparison.*`.
Graphs include the paired KPI comparison and eligible-meter hourly demand/PV
curves, with backing CSV under `results/charts/data/`. Aggregate PV is shown for
context; transfers always use the individual owner's surplus, not pooled PV.

The direct-PV KPI sums `min(PV, demand)` before battery operations. It is separate
from battery charging/discharging. When daily demand moves into unused own PV,
direct use rises and offered surplus falls. P2P volume can decrease even if grid
imports or costs improve. Compare fixed/shifted conditions within the same A–F
policy; do not attribute simultaneous regulation and flexibility changes to one
mechanism. Ratios must be read alongside absolute energy and denominators.

This model schedules divisible energy, not identified appliances. It excludes
task deadlines, minimum run times, thermal state, comfort, user consent, ramp
limits and forecast uncertainty. The heuristic is deterministic, not an optimizer;
six-hour advancement assumes tasks can be planned day-ahead. No physical peak
rating is inferred from the relative rebound cap. The original daily load shape
in the household metadata remains the baseline; actual scenario consumption is
recorded in hourly input/output files.
