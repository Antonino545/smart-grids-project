# Current mixed-building validation

On 21 October 2026 the accepted model changed from 100 individual households to
100 aggregate building meters: 50 small houses, 30 blocks, 10 supermarkets and
10 schools. There are 55 battery owners and 619 residential dwelling units in
the seeded realization. A block has one roof and one meter aggregating its flats.

The full suite passed **65 tests in 14.93 seconds**. Tests verify the type mix,
single-roof PV sizing, higher demand with more floors, school weekend reduction,
commercial night base load, type-dependent storage, reproducibility, chart-data
reconciliation and all original energy, money, reward and blockchain rules.
The optional residential-baseline configuration reproduces the original P2P and
PV energy volumes. All six mixed-building scenarios completed real runs and
passed independent exported-artifact verification. See `current_validation.json`.

Earlier results below are historical evidence for the old residential model.
They are not the current mixed-building outputs. Baseline comparisons and report
are preserved under `docs/baseline/` and `output/pdf/`.

---

# Recorded validation

Verified on 20 October 2026. Presentation preparation and ZIP packaging are deferred.

Environment: Python 3.14.7, Darwin arm64.

Installed dependencies: numpy 2.5.4, pandas 2.3.3, matplotlib 3.11.2, pytest 9.1.1.

## Automated suite

`python -m pytest -q`: **52 passed in 5.57 seconds** in the final full-suite run. The six-scenario execution and independent exported-result verification also succeeded after the chart layout adjustments.

The suite covers composition, synthetic and CSV inputs, forecast cutoff, battery bounds/losses/carry-over, neighborhood and aggregator matching, grid settlement, funded rewards, fees, blockchain integrity/tampering, zero-denominator KPIs, exported artifact validation and exported input tampering.

## Real execution

`python main.py --include-priority` completed all six scenarios with 100 households and 24 hours each. See `execution.log` for the captured output. Inputs are synthetic and share one verified hash.

| Scenario | P2P kWh | Share % | Hourly blocks | Internal trades |
|---|---:|---:|---:|---:|
| A | 8.934787 | 0.626490 | 24 | 57 |
| B | 18.655817 | 1.308110 | 24 | 86 |
| C | 12.822161 | 0.682733 | 24 | 82 |
| D | 26.765581 | 1.425168 | 24 | 132 |
| E | 10.709416 | 0.570237 | 24 | 68 |
| F | 21.800913 | 1.160818 | 24 | 111 |

Maximum absolute community energy reconciliation error: 2.27e-13 kWh.

Maximum absolute financial reconciliation error: 1.42e-14 EUR.

`python scripts/verify_results.py` independently reopened every scenario, recomputed the input hash, validated each saved chain against the CSV journal, matched transaction payments and rewards, checked each household-hour energy balance, and matched regulator funds to the cash ledger. All six passed.

`python -m pip check`: no broken requirements found.

## Artifact review and limitations

The six PNG chart sets were rendered and visually inspected. Aggregator volumes use a separate scale so they remain visible beside much larger grid volumes. Source CSV/JSON exports accompany charts. No claim is made about physical devices or real electricity-market observations.

The project was exercised on Python 3.14.7. Python 3.11+ compatibility follows the language features and dependency ranges, but other Python versions were not executed here. Synthetic profiles are illustrative and are not calibrated to a real community.

The presentation and ZIP packaging are deferred at the user's request. No archive is included and no files have been submitted.

## Additional result charts

The extended suite passed **55 tests in 8.64 seconds** after adding six further
chart types: hourly profiles, surplus destinations, household cost distributions,
regulation differences, battery energy flows and internal transaction prices.
All six were rendered and visually inspected. Their source data is exported under
`results/charts/data/`. Checks reconcile plotted surplus components with available
surplus, household cost totals with the ledger and battery flows with inventory
changes. A new six-scenario execution preserved the original numerical outcomes.

## Community distribution schematic

The square community map displays one neighborhood per row, one marker per
household, ownership type and installed PV capacity. The 100 cells were checked
against the saved experiment household table, including exact group, ownership
and PV attributes. Neighborhood battery counts are 6, 6, 5, 5, 6, 5, 6, 5, 5, 6.
Map coordinates are display positions only and do not change trading eligibility,
energy flows or ownership. PNG/SVG renderings were visually inspected. The full
suite passed **58 tests in 9.24 seconds** on 21 October 2026.

## Automatic map generation and PDF inclusion

A fresh `python main.py --include-priority --output /tmp/smartgrid-map-pdf-run`
completed all six scenarios and generated the community map and its CSV data.
The comparison JSON remained identical to the recorded experiment. An end-to-end
command-line test checks PNG/SVG generation and every mapped household against
the run's own exported community. The full suite passed **59 tests in 12.38 seconds**.
The PDF report now includes a dedicated community-layout page.

## Team parameter guide

The current mixed-building PDF has 21 pages. Pages 11–21 document all 154
configuration values from the saved run, including units, effects, type-specific
settings, inactive legacy fields, worked examples and commands for controlled
experiments. The reference builder checks coverage against every configuration
leaf and rejects undocumented or removed fields.

On 21 October 2026, the full suite passed **69 tests in 16.25 seconds**, including
four new parameter-reference checks. The PDF was generated successfully, all 21
pages were rendered, and their layout was visually inspected. This documentation
change does not alter simulation logic, inputs or numerical results.
