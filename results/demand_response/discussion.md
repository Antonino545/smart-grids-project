# Experiment discussion

These are model outputs for the recorded inputs and assumptions, not evidence of real-world performance.

| Scenario | P2P kWh | P2P share % | Imports kWh | Exports kWh | Household net cost EUR |
|---|---:|---:|---:|---:|---:|
| A | 717.111 | 18.977 | 17556.021 | 2213.610 | 5133.990 |
| B | 2233.312 | 59.100 | 16492.114 | 1149.703 | 5010.404 |
| C | 940.910 | 19.742 | 17927.841 | 2839.881 | 5207.960 |
| D | 2855.926 | 59.921 | 16519.794 | 1431.834 | 4992.426 |
| E | 932.281 | 19.561 | 17454.472 | 2191.225 | 5104.868 |
| F | 2845.301 | 59.698 | 16100.317 | 924.588 | 4887.963 |
| G | 2064.679 | 54.638 | 16625.787 | 1283.376 | 4927.137 |
| H | 2268.727 | 60.037 | 16385.219 | 1042.808 | 4913.785 |
| I | 1886.956 | 49.935 | 16755.101 | 1412.690 | 4942.849 |
| J | 2233.312 | 59.100 | 16492.114 | 1149.703 | 4878.652 |
| K | 2358.964 | 62.425 | 16340.214 | 997.803 | 4902.163 |

## Regulation comparisons
- B versus A: regulation increased P2P energy (difference +1516.201 kWh).
- D versus C: regulation increased P2P energy (difference +1915.017 kWh).
- F versus E: regulation increased P2P energy (difference +1913.021 kWh).

## Regulator policy variants (each compared with B)

| Scenario | Change | P2P kWh vs B | Fees EUR | Rewards EUR | Refunds EUR | Fund left EUR | Household cost vs B EUR |
|---|---|---:|---:|---:|---:|---:|---:|
| B | reference | +0.000 | 176.42 | 44.67 | 0.00 | 131.75 | +0.00 |
| G | B with a lower grid fee (EUR 0.0025/kWh) | -168.633 | 44.77 | 28.37 | 0.00 | 16.40 | -83.27 |
| H | B with a bigger reward (EUR 0.075/kWh upper tier, 0.0375 lower) | +35.415 | 174.28 | 113.49 | 0.00 | 60.79 | -96.62 |
| I | B, fee only on grid energy a neighbour could have traded | -346.356 | 15.81 | 14.73 | 0.00 | 1.08 | -67.55 |
| J | B, leftover fund refunded to P2P traders at day end | +0.000 | 176.42 | 44.67 | 131.75 | 0.00 | -131.75 |
| K | B, reward rate sized each hour to spend the fund | +125.652 | 173.38 | 113.41 | 0.00 | 59.97 | -108.24 |

Price guidance and funded discounts can make more offers compatible. A reward cannot create PV surplus or demand, and does not guarantee improvement for other seeds or inputs.

## Battery interpretation

Self-consumption-first batteries remove PV surplus before trading and reduce later demand. Compare absolute P2P energy alongside its changing denominator. E/F defer charging until after P2P, so their offered-surplus denominator includes PV subsequently stored. Compare raw PV surplus as well.

Initial stored battery energy is an exogenous inventory. Final stored energy can differ between strategies. Costs exclude inventory valuation, battery investment, degradation, taxes and network charges other than the modeled regulator fee.

## Accounting and limits

Internal payments transfer money between households. Fees transfer money to the regulator, and rewards transfer it back. Household net costs include these transfers. Household-plus-regulator net costs equal net external-grid payments. Every summary reports numerical energy and financial reconciliation errors.

The model uses copper-plate energy settlement without feeder limits, voltage, power flow, battery aging or strategic learning. A single deterministic day supports a demonstration, not a statistical claim. No improvement is forced.
