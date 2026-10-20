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
