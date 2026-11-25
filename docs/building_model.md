# Mixed building community

The extended design contains **150 aggregate building meters: 100 original
prosumers and 50 added consumer-only buildings**, not 150 individual households. Apartment blocks
represent all their homes at one meter. Commercial buildings and schools
also have one meter each. The identifier `household_id` remains for compatibility.
H001-H100 identify unchanged prosumers; H101-H150 identify consumers.

## Initial composition

The default shares are 56% small houses, 30% apartment blocks, 10% supermarkets
and 4% schools, giving 56/30/10/4 prosumers and 28/15/5/2 consumers (84 houses,
45 blocks, 15 supermarkets and 6 schools; 150 in total). Counts are rounded over
the whole pool (largest remainder), then dealt round-robin over the ten groups, so
every group has exactly 10 prosumers and 5 consumers and a type with fewer
buildings than groups (the 4 prosumer schools) lands in different groups.
Consumers have the same geometry/load rules for their type, but zero installed PV
and no batteries. They can only buy energy through P2P, aggregator or grid.
No group is consumer-only or prosumer-only. Positions within each row are shuffled
with a fixed seed, independently of battery assignment. The 55 battery-owning IDs
stay unchanged: each neighborhood has five or six owners. Counterfactual C/D
disable storage without changing type, roof, identity, home count, demand inputs
or battery ownership metadata.

## Area: Turin (Torino)

The community is placed in Turin (45.07 N, 7.69 E, about 240 m). Values below come
from public sources where they exist and are engineering choices otherwise:

| Quantity | Value | Source / reasoning |
|---|---|---|
| Best fixed panel tilt, whole year | 40 deg, south, 1,368 kWh/kW/yr | JRC PVGIS 5.2 |
| June yield at 10 / 20 / 30 deg | 4.92 / 4.87 / 4.75 kWh/kW/day | JRC PVGIS 5.2 |
| June light on panel, average / clear day (20 deg) | 6.54 / 7.90 kWh/m2/day | JRC PVGIS 5.2 daily profile |
| Total PV losses (cables, inverter, heat, reflection) | about 22-25% | JRC PVGIS 5.2 (14% system + temperature/angle) |
| Tiled roof pitch in northern Italy | 35-45% slope = 19-24 deg | Italian roofing guides |
| Average home size in Italian cities | 93.5 m2 | ISTAT 2023 |
| Household electricity | 2,200 kWh/yr (2 people) to 2,700 kWh/yr (typical) | ARERA reference values |
| Household size, Piedmont | 2.1 people | Regione Piemonte |

## Geometry and sizing assumptions

A **home** is one flat or house where one family lives. A block holds many homes
behind one meter.

| Type | Count | Roof m2 | Floors | Homes | Base energy | Panel tilt | Roof covered | PV kW (roof-based) | PV limit | Battery |
|---|---:|---:|---:|---|---|---:|---:|---:|---:|---|
| Small house | 84 | 80-140 | 1-2 | 1 | 7-12 kWh/home/day | 20 deg | 22-35% | 3.5-9.8 | 10 kW | 10 kWh / 3 kW |
| Apartment block | 45 | 250-500 | 4-8 | 80% of footprint / 70-110 m2, per floor | 5-8 kWh/home/day | 15 deg | 30-45% | 15-45 | 50 kW | 40 kWh / 12 kW |
| Supermarket | 15 | 800-1600 | 1 | 0 | 0.8-1.3 kWh/m2/day | 10 deg | 40-55% | 64-176 | 200 kW | 100 kWh / 30 kW |
| School | 6 | 700-1600 | 2-4 | 0 | 0.08-0.15 kWh/m2/day | 15 deg | 30-45% | 42-144 | 150 kW | 60 kWh / 18 kW |

Why these values:

- **Panel tilt.** House panels lie flush on the south pitch of a tiled roof, about
  20 deg. Flat roofs (blocks, schools, supermarkets) use racks. Low racks (10-15 deg)
  give the highest June yield in Turin and need less space between rows, so more of
  the roof can be covered; supermarkets use 10 deg to cover their large roofs densely.
  For a whole year, 40 deg would be best (PVGIS), about 7-11% more energy per kW.
- **Roof covered** is the share of the footprint covered by modules after fire
  setbacks, chimneys, lift rooms, vents and gaps between rows. On a pitched house
  roof only the south side is used, so it stays below half of the footprint. On
  flat roofs, rows at 15 deg need about 1.6 module lengths of spacing to avoid
  winter shading in Turin, so at most about 60% of the free roof is covered.
- **PV limit** sits just above the largest roof-based size. The roof decides the
  size; the limit is only a safety cap and never binds with the defaults.
- **Homes in a block** follow from the footprint: 80% of each floor is living
  space, divided by a home size drawn between 70 and 110 m2 (city average 93.5 m2).
  This keeps floor area, home count and demand consistent with each other.
- **Home demand.** About 1,800-2,900 kWh/yr per flat (5-8 kWh/day) and 2,600-4,400
  kWh/yr for a detached house (7-12 kWh/day), bracketing the ARERA reference values
  with some summer cooling.

The roof is an approximate building footprint. Total floor area = roof area x
floors. Each building has **one roof regardless of its height**. PV installed kW is:

```
min(single_roof_m2 * usable_roof_fraction * pv_density_kw_m2, type_pv_limit_kw)
```

with 0.20 kW per m2 of module (about 20%-efficient panels). Floors and homes do not
enter the PV formula.

## Solar production

Every hour, `src/solar.py` computes the sun position over Turin (NOAA formulas),
the clear-sky light (Meinel beam model with air mass and altitude, Liu-Jordan
diffuse) and the light reaching each panel from its tilt and direction (beam +
sky diffuse + ground reflection, albedo 0.20), averaged over 5-minute steps.
`forecast.clear_sky_transmittance = 0.66` makes the clear June day match PVGIS
within about 1% at 10-30 deg. One seeded cloud factor per hour (0.65-1.0, mean
0.825) is shared by all buildings and reproduces the PVGIS average/clear June
ratio (0.83). PV kWh = kW x panel light / 1000 x 0.75, capped at the installed kW;
0.75 is the PVGIS June output/light ratio for Turin. The expected June yield is
about 4.9 kWh per installed kW per day, as in PVGIS. On 15 June the sun rises at
about 05:40 and sets at about 21:15 local time; solar noon is about 13:30.

A `forecast.weather_csv` file gives **horizontal** light (GHI). Each hour it is
moved onto every panel tilt using the clear-sky ratio of panel to horizontal light.

Battery-owning buildings scale the configured base battery's capacity **and**
power by 1/4/10/6 for house/block/supermarket/school. All retain 95% efficiency
in each direction and SOC 10-90%, initially 20%. These scales are configurable.
The self-consumption/P2P-priority policy and PV-only charging rule are unchanged.

## Time-dependent electricity demand

- Houses and blocks use household-specific morning and evening peaks. Block
  demand is the sum over its homes, not an independent roof per flat.
- Supermarkets have a nonzero all-day base load (illustrating refrigeration and
  essential equipment), plus an operating load during 07:00-22:00. Weekend daily
  energy defaults to 90% of weekday energy.
- Schools have a lower base load and operating activity during 08:00-17:00 on
  weekdays. Weekend operating activity is disabled and total daily energy is 15%
  of the weekday baseline. This is a weekday/weekend calendar, not a holiday or
  school-term calendar. In Piedmont lessons end around 10 June, so a 15 June run
  overstates school use (exams still keep many schools open); this is a simplification.
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
area, homes, panel tilt/direction and type-specific battery attributes. `building_type_summary.csv`
and `building_type_hourly.csv` support the automatically generated
`building_type_profiles.png/.svg`. The latter plots mean demand and PV per building
in each type, not totals over types with unequal counts. `comparison.json` states
the participant unit, building counts and total homes.

The earlier homogeneous-house model remains runnable with:

```bash
python main.py --config config/residential_baseline.json --include-priority --output results/legacy_run
```

Historical residential comparison values are preserved under `docs/baseline/`,
and its PDF is preserved as `output/pdf/smart_grids_residential_baseline_report.pdf`.
Mixed-building outcomes are a new experiment, not a like-for-like improvement
over the old community. Historical filenames containing `household` remain stable,
but current charts and documentation describe building meter costs.
