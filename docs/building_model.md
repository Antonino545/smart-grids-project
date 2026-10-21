# Mixed building community

The current design, accepted on 21 October 2026, contains **100 buildings with
aggregate electricity meters**, not 100 individual households. Apartment blocks
represent all their dwelling units at one meter. Commercial buildings and schools
also have one meter each. The historical identifier `household_id` and H001-H100
are retained in code/CSV files for compatibility; they now identify building meters.

## Initial composition

Each of ten neighborhoods contains five small houses, three apartment blocks,
one supermarket and one school. Positions within the row are shuffled with a
fixed seed, independently of battery assignment. The defaults give 50/30/10/10
buildings. The existing 55 battery-owning IDs remain unchanged: each neighborhood
has five or six owners. Counterfactual C/D disable storage without changing type,
roof, identity, dwelling count, demand inputs or battery ownership metadata.

Type shares are configurable in the `buildings.types` section of JSON. Within
each group, fractional counts use largest-remainder rounding. For group sizes
other than ten, the actual exported composition may differ from the requested
fractions. Building identities remain fixed across the six experiments.

## Geometry and sizing assumptions

**All ranges below are synthetic engineering defaults, not measured building
stock, equipment recommendations or professor requirements.** The selected values
allow a heterogeneous teaching simulation and must be calibrated for real use.

| Type | Count | Single roof m2 | Floors | Demand basis | Base energy range | Battery capacity / power |
|---|---:|---:|---:|---|---|---|
| Small house | 50 | 70-150 | 1-2 | One dwelling | 8-24 kWh/dwelling/day | 10 kWh / 3 kW |
| Apartment block | 30 | 180-360 | 4-10 | 2-4 dwellings per floor | 8-20 kWh/dwelling/day | 40 kWh / 12 kW |
| Supermarket | 10 | 600-1400 | 1 | Total floor area | 0.5-1.1 kWh/m2/day | 100 kWh / 30 kW |
| School | 10 | 700-1600 | 2-3 | Total floor area | 0.08-0.18 kWh/m2/day | 60 kWh / 18 kW |

The roof is an approximate building footprint. Total floor area = roof area x
floors. For blocks, dwelling count = floors x dwellings per floor. For small
houses it is one dwelling; schools/supermarkets count zero residential dwellings.
There are more than 100 dwelling units in the default community because blocks
contain many apartments. Exported totals describe the actual seeded realization.

Each building has **one roof regardless of its height**. PV installed kW is:

```
min(single_roof_m2 * usable_roof_fraction * pv_density_kw_m2, type_pv_limit_kw)
```

Default usable fraction is 35-65%, density 0.20 kW/m2, PV limits 12 kW for small
houses, 100 kW for blocks, and 300 kW for supermarkets/schools. Floors and dwelling
counts do not enter the PV formula. Increasing floors increases the load basis
without manufacturing extra rooftop area. Identical weather is converted into
PV generation separately for each building's installed capacity.

Battery-owning buildings scale the configured base battery's capacity **and**
power by 1/4/10/6 for house/block/supermarket/school. All retain 95% efficiency
in each direction and SOC 10-90%, initially 20%. These scales are configurable.
The self-consumption/P2P-priority policy and PV-only charging rule are unchanged.

## Time-dependent electricity demand

- Houses and blocks use household-specific morning and evening peaks. Block
  demand is the aggregate of its dwelling count, not an independent roof per flat.
- Supermarkets have a nonzero all-day base load (illustrating refrigeration and
  essential equipment), plus an operating load during 07:00-22:00. Weekend daily
  energy defaults to 90% of weekday energy.
- Schools have a lower base load and operating activity during 08:00-17:00 on
  weekdays. Weekend operating activity is disabled and total daily energy is 15%
  of the weekday baseline. This is a weekday/weekend calendar, not a holiday or
  school-term calendar; June school operation is an explicit simplifying choice.
- Within each type, roof size, floor count, daily energy intensity, profile timing
  and hourly variation differ by building. Each calendar day gets a seeded
  multiplier within +/-8%, while retaining its type-specific hourly shape.

The base daily energy range is distinct from the realized daily consumption after
weekend and day-variation factors. Inputs are generated once, reused across all
scenarios, and never altered to force a trading improvement. Real demand CSVs
replace synthetic demand entirely and must use aggregate-meter quantities.
HVAC/weather sensitivity, holidays, occupancy sensors and learned profiles are
not implemented. Geometry is fixed through an experiment; energy varies hourly
and by date. The default run still has 24 one-hour steps.

## Configuration

`config/default.json` contains all type parameters. Partial type overrides retain
the rest of that archetype's defaults. Example:

```json
{
  "buildings": {
    "types": {
      "apartment_block": {"floors_min": 6, "floors_max": 12},
      "school": {"weekend_multiplier": 0.10},
      "supermarket": {"opening_hour": 8, "closing_hour": 21}
    }
  }
}
```

`households` configuration continues to control offer ranges, residential peak
shapes and profile noise. Its legacy PV/daily-demand ranges and `base_demand_weight` apply only when
`buildings.enabled` is false. With the building model enabled, type parameters
control physical sizing and energy baselines.

## Outputs and compatibility

The community map uses separate HOUSE, BLOCK, SHOP and SCHOOL silhouettes/labels.
BLOCK labels include floor counts. Blue/gold show battery ownership, with a B
badge for accessibility. Icons are schematic and not scaled land parcels or an
electrical feeder map. All P2P members of a row remain eligible regardless of
visual distance.

`households.csv` and `community_layout.csv` add building type, roof, floors, floor
area, dwelling units and type-specific battery attributes. `building_type_summary.csv`
and `building_type_hourly.csv` support the automatically generated
`building_type_profiles.png/.svg`. The latter plots mean demand and PV per building
in each type, not totals over types with unequal counts. `comparison.json` states
the participant unit, building counts and total dwelling units.

The earlier homogeneous-house model remains runnable with:

```bash
python main.py --config config/residential_baseline.json --include-priority --output results/legacy_run
```

Historical residential comparison values are preserved under `docs/baseline/`,
and its PDF is preserved as `output/pdf/smart_grids_residential_baseline_report.pdf`.
Mixed-building outcomes are a new experiment, not a like-for-like improvement
over the old community. Historical filenames containing `household` remain stable,
but current charts and documentation describe building meter costs.
