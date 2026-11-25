# Experiment discussion

These are model outputs for the recorded inputs and assumptions, not evidence of real-world performance.

| Scenario | P2P kWh | P2P share % | Imports kWh | Exports kWh | Household net cost EUR |
|---|---:|---:|---:|---:|---:|
| A | 683.957 | 18.376 | 17138.740 | 2203.822 | 5009.393 |
| B | 2029.321 | 54.522 | 16228.097 | 1293.179 | 4925.465 |
| C | 914.790 | 19.261 | 17544.591 | 2864.308 | 5091.519 |
| D | 2676.823 | 56.361 | 16293.871 | 1613.587 | 4916.884 |
| E | 896.146 | 18.868 | 17022.480 | 2156.253 | 4977.369 |
| F | 2646.458 | 55.721 | 15836.542 | 1064.544 | 4803.172 |
| G | 1930.747 | 51.873 | 16313.623 | 1378.705 | 4827.849 |
| H | 2132.428 | 57.292 | 16044.243 | 1109.325 | 4807.382 |
| I | 1781.825 | 47.872 | 16445.847 | 1510.928 | 4844.332 |
| J | 2029.321 | 54.522 | 16228.097 | 1293.179 | 4790.838 |
| K | 2204.632 | 59.232 | 16056.453 | 1121.534 | 4809.391 |
| L | 2665.327 | 56.119 | 15829.845 | 1052.674 | 4746.839 |

## Regulation comparisons
- B versus A: regulation increased P2P energy (difference +1345.365 kWh).
- D versus C: regulation increased P2P energy (difference +1762.033 kWh).
- F versus E: regulation increased P2P energy (difference +1750.312 kWh).

## Regulator policy variants (each compared with B)

| Scenario | Change | P2P kWh vs B | Fees EUR | Rewards EUR | Refunds EUR | Fund left EUR | Household cost vs B EUR |
|---|---|---:|---:|---:|---:|---:|---:|
| B | reference | +0.000 | 175.21 | 40.59 | 0.00 | 134.63 | +0.00 |
| G | B with a lower grid fee (EUR 0.0025/kWh) | -98.575 | 44.23 | 27.75 | 0.00 | 16.48 | -97.62 |
| H | B with a bigger reward (EUR 0.075/kWh upper tier, 0.0375 lower) | +103.107 | 171.54 | 110.87 | 0.00 | 60.67 | -118.08 |
| I | B, fee only on grid energy a neighbour could have traded | -247.496 | 14.45 | 13.21 | 0.00 | 1.23 | -81.13 |
| J | B, leftover fund refunded to P2P traders at day end | +0.000 | 175.21 | 40.59 | 134.63 | 0.00 | -134.63 |
| K | B, reward rate sized each hour to spend the fund | +175.310 | 171.78 | 112.03 | 0.00 | 59.75 | -116.07 |

## Combined scenario L (F battery order + K fund-sized reward)

| Compared with | P2P kWh change | Meter cost change EUR | Meters + regulator change EUR | Final storage change kWh |
|---|---:|---:|---:|---:|
| F | +18.869 | -56.33 | -1.30 | +3.613 |
| K | +460.695 | -62.55 | -63.85 | -128.611 |

Price guidance and funded discounts can make more offers compatible. A reward cannot create PV surplus or demand, and does not guarantee improvement for other seeds or inputs.

## Battery interpretation

Self-consumption-first batteries remove PV surplus before trading and reduce later demand. Compare absolute P2P energy alongside its changing denominator. E/F defer charging until after P2P, so their offered-surplus denominator includes PV subsequently stored. Compare raw PV surplus as well.

Initial stored battery energy is an exogenous inventory. Final stored energy can differ between strategies. Costs exclude inventory valuation, battery investment, degradation, taxes and network charges other than the modeled regulator fee.

## Accounting and limits

Internal payments transfer money between households. Fees transfer money to the regulator, and rewards transfer it back. Household net costs include these transfers. Household-plus-regulator net costs equal net external-grid payments. Every summary reports numerical energy and financial reconciliation errors.

The model uses copper-plate energy settlement without feeder limits, voltage, power flow, battery aging or strategic learning. A single deterministic day supports a demonstration, not a statistical claim. No improvement is forced.
