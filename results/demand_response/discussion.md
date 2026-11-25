# Experiment discussion

These are model outputs for the recorded inputs and assumptions, not evidence of real-world performance.

| Scenario | P2P kWh | P2P share % | Imports kWh | Exports kWh | Household net cost EUR |
|---|---:|---:|---:|---:|---:|
| A | 681.362 | 18.306 | 17139.405 | 2204.487 | 5009.552 |
| B | 1969.772 | 52.922 | 16290.799 | 1355.881 | 4942.958 |
| C | 910.217 | 19.165 | 17531.581 | 2851.297 | 5088.396 |
| D | 2608.465 | 54.921 | 16386.604 | 1706.320 | 4942.362 |
| E | 891.311 | 18.767 | 17029.496 | 2173.045 | 4978.466 |
| F | 2589.059 | 54.513 | 15948.910 | 1177.392 | 4833.511 |
| G | 1898.355 | 51.003 | 16351.202 | 1416.284 | 4837.028 |
| H | 2112.323 | 56.752 | 16092.680 | 1157.761 | 4819.093 |
| I | 1726.712 | 46.392 | 16472.425 | 1537.506 | 4851.221 |
| J | 1969.772 | 52.922 | 16290.799 | 1355.881 | 4805.887 |
| K | 2164.392 | 58.151 | 16084.903 | 1149.985 | 4816.208 |
| L | 2629.188 | 55.358 | 15897.842 | 1120.463 | 4763.269 |

## Regulation comparisons
- B versus A: regulation increased P2P energy (difference +1288.410 kWh).
- D versus C: regulation increased P2P energy (difference +1698.248 kWh).
- F versus E: regulation increased P2P energy (difference +1697.748 kWh).

## Regulator policy variants (each compared with B)

| Scenario | Change | P2P kWh vs B | Fees EUR | Rewards EUR | Refunds EUR | Fund left EUR | Household cost vs B EUR |
|---|---|---:|---:|---:|---:|---:|---:|
| B | reference | +0.000 | 176.47 | 39.40 | 0.00 | 137.07 | +0.00 |
| G | B with a lower grid fee (EUR 0.0025/kWh) | -71.417 | 44.42 | 27.77 | 0.00 | 16.64 | -105.93 |
| H | B with a bigger reward (EUR 0.075/kWh upper tier, 0.0375 lower) | +142.551 | 172.50 | 111.75 | 0.00 | 60.75 | -123.87 |
| I | B, fee only on grid energy a neighbour could have traded | -243.060 | 15.60 | 13.86 | 0.00 | 1.74 | -91.74 |
| J | B, leftover fund refunded to P2P traders at day end | +0.000 | 176.47 | 39.40 | 137.07 | 0.00 | -137.07 |
| K | B, reward rate sized each hour to spend the fund | +194.620 | 172.35 | 112.61 | 0.00 | 59.74 | -126.75 |

## Combined scenario L (F battery order + K fund-sized reward)

| Compared with | P2P kWh change | Meter cost change EUR | Meters + regulator change EUR | Final storage change kWh |
|---|---:|---:|---:|---:|
| F | +40.130 | -70.24 | -11.90 | +4.877 |
| K | +464.796 | -52.94 | -54.35 | -127.409 |

Price guidance and funded discounts can make more offers compatible. A reward cannot create PV surplus or demand, and does not guarantee improvement for other seeds or inputs.

## Battery interpretation

Self-consumption-first batteries remove PV surplus before trading and reduce later demand. Compare absolute P2P energy alongside its changing denominator. E/F defer charging until after P2P, so their offered-surplus denominator includes PV subsequently stored. Compare raw PV surplus as well.

Initial stored battery energy is an exogenous inventory. Final stored energy can differ between strategies. Costs exclude inventory valuation, battery investment, degradation, taxes and network charges other than the modeled regulator fee.

## Accounting and limits

Internal payments transfer money between households. Fees transfer money to the regulator, and rewards transfer it back. Household net costs include these transfers. Household-plus-regulator net costs equal net external-grid payments. Every summary reports numerical energy and financial reconciliation errors.

The model uses copper-plate energy settlement without feeder limits, voltage, power flow, battery aging or strategic learning. A single deterministic day supports a demonstration, not a statistical claim. No improvement is forced.
