# Input data formats

All files are UTF-8 CSV with headers and decimal points. Every timestamp must
include an offset, for example `2026-06-15T12:00:00+02:00`. One row represents an
hour beginning at that timestamp. Energy is integrated over that one-hour step.
Relative file paths resolve from the working directory used to run `main.py`.

## Weather forecast

Set `forecast.weather_csv`:

```csv
timestamp,irradiance_w_m2
2026-06-15T00:00:00+02:00,0
2026-06-15T01:00:00+02:00,0
```

Supply one row for **every simulation hour**. Irradiance is nonnegative and finite.
Duplicate instants and missing hours fail validation. Nighttime irradiance must
be zero according to configured sunrise/sunset. Update these settings for the
chosen season/location. PV output is capped at installed power times one hour.
Weather rows must represent forecasts available at forecast issuance, or clearly
labeled hindcast inputs. The code cannot determine whether a supplied weather
CSV secretly contains future actual measurements. Record source, retrieval date,
forecast issuance and transformations in `data/raw/PROVENANCE.md` when adding it.

## Demand forecast

Set `forecast.demand_csv`:

```csv
timestamp,household_id,demand_kwh
2026-06-15T00:00:00+02:00,H001,0.45
2026-06-15T00:00:00+02:00,H002,0.60
```

Supply every `(timestamp, household_id)` combination, with IDs matching the
exported meter table (H001 through H100 by default). Each ID now represents an
aggregate building meter, including all flats for a block; provide whole-building
demand rather than per-flat demand. Demand must be finite and
nonnegative. Missing combinations and duplicates fail. Prepare demand forecasts
using observations available before simulation start. The simulator uses the
provided demand forecast directly; it does not fit a demand-learning model.

## Historical electricity prices

Set `forecast.historical_prices_csv`:

```csv
timestamp,price_eur_kwh
2026-06-14T00:00:00+02:00,0.15
2026-06-14T01:00:00+02:00,0.14
```

Supply at least one observation for each hour of day **before** the simulation
start. Reference prices are the unweighted mean of earlier observations with the
same clock hour. Negative prices are accepted; non-finite values fail. Convert
EUR/MWh source prices to EUR/kWh by dividing by 1000 before import. Rows at or
after the cutoff cannot influence predictions. Duplicate timestamps are rejected.
Forecasts remain fixed through the experiment rather than updating from future
observations during simulation.

## Example override file

```json
{
  "forecast": {
    "start_timestamp": "2026-06-15T00:00:00+02:00",
    "weather_csv": "data/raw/weather_forecast.csv",
    "demand_csv": "data/raw/demand_forecast.csv",
    "historical_prices_csv": "data/raw/prices.csv"
  }
}
```

The short CSV snippets above illustrate columns only and do not provide complete
coverage. Each input type independently falls back to synthetic data when its
path is null. Output source labels reveal which fallback was used.
