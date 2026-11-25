# Experiment discussion

These are model outputs for the recorded inputs and assumptions, not evidence of real-world performance.

| Scenario | P2P kWh | P2P share % | Imports kWh | Exports kWh | Household net cost EUR |
|---|---:|---:|---:|---:|---:|
| A | 740.067 | 18.278 | 17785.533 | 2443.123 | 5189.073 |
| B | 2349.577 | 58.030 | 16704.619 | 1362.209 | 5063.330 |
| C | 962.592 | 19.114 | 18148.926 | 3060.965 | 5261.020 |
| D | 2958.634 | 58.747 | 16674.797 | 1586.837 | 5030.673 |
| E | 953.911 | 18.941 | 17705.956 | 2442.330 | 5165.247 |
| F | 2941.264 | 58.403 | 16263.184 | 1084.672 | 4928.528 |
| G | 2189.921 | 54.086 | 16834.677 | 1492.266 | 4977.751 |
| H | 2374.048 | 58.634 | 16583.259 | 1240.848 | 4962.689 |
| I | 1998.394 | 49.356 | 16981.230 | 1638.820 | 4997.342 |
| J | 2349.577 | 58.030 | 16704.619 | 1362.209 | 4929.653 |
| K | 2470.890 | 61.026 | 16546.269 | 1203.858 | 4953.249 |
| L | 2943.493 | 58.447 | 16268.337 | 1090.423 | 4879.013 |

## Regulation comparisons
- B versus A: regulation increased P2P energy (difference +1609.510 kWh).
- D versus C: regulation increased P2P energy (difference +1996.041 kWh).
- F versus E: regulation increased P2P energy (difference +1987.353 kWh).

## Regulator policy variants (each compared with B)

| Scenario | Change | P2P kWh vs B | Fees EUR | Rewards EUR | Refunds EUR | Fund left EUR | Household cost vs B EUR |
|---|---|---:|---:|---:|---:|---:|---:|
| B | reference | +0.000 | 180.67 | 46.99 | 0.00 | 133.68 | +0.00 |
| G | B with a lower grid fee (EUR 0.0025/kWh) | -159.656 | 45.82 | 28.93 | 0.00 | 16.88 | -85.58 |
| H | B with a bigger reward (EUR 0.075/kWh upper tier, 0.0375 lower) | +24.472 | 178.24 | 116.08 | 0.00 | 62.16 | -100.64 |
| I | B, fee only on grid energy a neighbour could have traded | -351.183 | 16.46 | 15.16 | 0.00 | 1.30 | -65.99 |
| J | B, leftover fund refunded to P2P traders at day end | +0.000 | 180.67 | 46.99 | 133.68 | 0.00 | -133.68 |
| K | B, reward rate sized each hour to spend the fund | +121.313 | 177.50 | 115.90 | 0.00 | 61.60 | -110.08 |

## Combined scenario L (F battery order + K fund-sized reward)

| Compared with | P2P kWh change | Meter cost change EUR | Meters + regulator change EUR | Final storage change kWh |
|---|---:|---:|---:|---:|
| F | +2.229 | -49.52 | +1.20 | -1.926 |
| K | +472.603 | -74.24 | -76.57 | -138.288 |

Price guidance and funded discounts can make more offers compatible. A reward cannot create PV surplus or demand, and does not guarantee improvement for other seeds or inputs.

## Battery interpretation

Self-consumption-first batteries remove PV surplus before trading and reduce later demand. Compare absolute P2P energy alongside its changing denominator. E/F defer charging until after P2P, so their offered-surplus denominator includes PV subsequently stored. Compare raw PV surplus as well.

Initial stored battery energy is an exogenous inventory. Final stored energy can differ between strategies. Costs exclude inventory valuation, battery investment, degradation, taxes and network charges other than the modeled regulator fee.

## Accounting and limits

Internal payments transfer money between households. Fees transfer money to the regulator, and rewards transfer it back. Household net costs include these transfers. Household-plus-regulator net costs equal net external-grid payments. Every summary reports numerical energy and financial reconciliation errors.

The model uses copper-plate energy settlement without feeder limits, voltage, power flow, battery aging or strategic learning. A single deterministic day supports a demonstration, not a statistical claim. No improvement is forced.
