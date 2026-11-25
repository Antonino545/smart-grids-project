# Experiment discussion

These are model outputs for the recorded inputs and assumptions, not evidence of real-world performance.

| Scenario | P2P kWh | P2P share % | Imports kWh | Exports kWh | Household net cost EUR |
|---|---:|---:|---:|---:|---:|
| A | 701.814 | 17.580 | 17395.018 | 2460.100 | 5070.900 |
| B | 2129.838 | 53.350 | 16324.186 | 1389.267 | 4948.437 |
| C | 932.997 | 18.587 | 17774.732 | 3094.449 | 5146.753 |
| D | 2768.859 | 55.160 | 16489.640 | 1809.356 | 4965.944 |
| E | 913.490 | 18.198 | 17276.650 | 2409.223 | 5038.442 |
| F | 2738.552 | 54.557 | 16039.562 | 1273.474 | 4853.819 |
| G | 2018.108 | 50.551 | 16420.949 | 1486.030 | 4853.951 |
| H | 2212.267 | 55.414 | 16213.603 | 1278.684 | 4849.724 |
| I | 1873.841 | 46.937 | 16580.544 | 1645.625 | 4876.653 |
| J | 2129.838 | 53.350 | 16324.186 | 1389.267 | 4813.900 |
| K | 2296.680 | 57.529 | 16174.057 | 1239.138 | 4839.237 |
| L | 2758.094 | 54.946 | 16019.336 | 1246.383 | 4793.706 |

## Regulation comparisons
- B versus A: regulation increased P2P energy (difference +1428.024 kWh).
- D versus C: regulation increased P2P energy (difference +1835.862 kWh).
- F versus E: regulation increased P2P energy (difference +1825.062 kWh).

## Regulator policy variants (each compared with B)

| Scenario | Change | P2P kWh vs B | Fees EUR | Rewards EUR | Refunds EUR | Fund left EUR | Household cost vs B EUR |
|---|---|---:|---:|---:|---:|---:|---:|
| B | reference | +0.000 | 177.13 | 42.60 | 0.00 | 134.54 | +0.00 |
| G | B with a lower grid fee (EUR 0.0025/kWh) | -111.730 | 44.77 | 27.94 | 0.00 | 16.83 | -94.49 |
| H | B with a bigger reward (EUR 0.075/kWh upper tier, 0.0375 lower) | +82.429 | 174.92 | 112.56 | 0.00 | 62.36 | -98.71 |
| I | B, fee only on grid energy a neighbour could have traded | -255.997 | 15.01 | 13.79 | 0.00 | 1.23 | -71.78 |
| J | B, leftover fund refunded to P2P traders at day end | +0.000 | 177.13 | 42.60 | 134.54 | 0.00 | -134.54 |
| K | B, reward rate sized each hour to spend the fund | +166.842 | 174.13 | 112.76 | 0.00 | 61.37 | -109.20 |

## Combined scenario L (F battery order + K fund-sized reward)

| Compared with | P2P kWh change | Meter cost change EUR | Meters + regulator change EUR | Final storage change kWh |
|---|---:|---:|---:|---:|
| F | +19.542 | -60.11 | -4.44 | +5.100 |
| K | +461.414 | -45.53 | -46.85 | -132.839 |

Price guidance and funded discounts can make more offers compatible. A reward cannot create PV surplus or demand, and does not guarantee improvement for other seeds or inputs.

## Battery interpretation

Self-consumption-first batteries remove PV surplus before trading and reduce later demand. Compare absolute P2P energy alongside its changing denominator. E/F defer charging until after P2P, so their offered-surplus denominator includes PV subsequently stored. Compare raw PV surplus as well.

Initial stored battery energy is an exogenous inventory. Final stored energy can differ between strategies. Costs exclude inventory valuation, battery investment, degradation, taxes and network charges other than the modeled regulator fee.

## Accounting and limits

Internal payments transfer money between households. Fees transfer money to the regulator, and rewards transfer it back. Household net costs include these transfers. Household-plus-regulator net costs equal net external-grid payments. Every summary reports numerical energy and financial reconciliation errors.

The model uses copper-plate energy settlement without feeder limits, voltage, power flow, battery aging or strategic learning. A single deterministic day supports a demonstration, not a statistical claim. No improvement is forced.
