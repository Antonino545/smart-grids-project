# Experiment discussion

These are model outputs for the recorded inputs and assumptions, not evidence of real-world performance.

| Scenario | P2P kWh | P2P share % | Imports kWh | Exports kWh | Household net cost EUR |
|---|---:|---:|---:|---:|---:|
| A | 698.534 | 17.497 | 17377.966 | 2443.047 | 5066.807 |
| B | 2058.761 | 51.569 | 16447.299 | 1512.380 | 4981.868 |
| C | 929.440 | 18.516 | 17775.934 | 3095.650 | 5147.041 |
| D | 2700.887 | 53.806 | 16542.269 | 1861.985 | 4980.986 |
| E | 908.288 | 18.095 | 17263.550 | 2397.937 | 5035.189 |
| F | 2681.961 | 53.429 | 16110.597 | 1332.822 | 4874.005 |
| G | 1974.339 | 49.455 | 16513.354 | 1578.435 | 4876.337 |
| H | 2178.665 | 54.573 | 16295.833 | 1360.914 | 4869.606 |
| I | 1809.618 | 45.329 | 16651.380 | 1716.462 | 4894.179 |
| J | 2058.761 | 51.569 | 16447.299 | 1512.380 | 4843.447 |
| K | 2254.390 | 56.470 | 16248.243 | 1313.325 | 4857.063 |
| L | 2711.769 | 54.023 | 16069.792 | 1290.192 | 4806.278 |

## Regulation comparisons
- B versus A: regulation increased P2P energy (difference +1360.228 kWh).
- D versus C: regulation increased P2P energy (difference +1771.447 kWh).
- F versus E: regulation increased P2P energy (difference +1773.673 kWh).

## Regulator policy variants (each compared with B)

| Scenario | Change | P2P kWh vs B | Fees EUR | Rewards EUR | Refunds EUR | Fund left EUR | Household cost vs B EUR |
|---|---|---:|---:|---:|---:|---:|---:|
| B | reference | +0.000 | 179.60 | 41.18 | 0.00 | 138.42 | +0.00 |
| G | B with a lower grid fee (EUR 0.0025/kWh) | -84.423 | 45.23 | 28.19 | 0.00 | 17.04 | -105.53 |
| H | B with a bigger reward (EUR 0.075/kWh upper tier, 0.0375 lower) | +119.904 | 176.57 | 114.06 | 0.00 | 62.51 | -112.26 |
| I | B, fee only on grid energy a neighbour could have traded | -249.143 | 16.20 | 14.45 | 0.00 | 1.75 | -87.69 |
| J | B, leftover fund refunded to P2P traders at day end | +0.000 | 179.60 | 41.18 | 138.42 | 0.00 | -138.42 |
| K | B, reward rate sized each hour to spend the fund | +195.629 | 175.62 | 114.23 | 0.00 | 61.39 | -124.81 |

## Combined scenario L (F battery order + K fund-sized reward)

| Compared with | P2P kWh change | Meter cost change EUR | Meters + regulator change EUR | Final storage change kWh |
|---|---:|---:|---:|---:|
| F | +29.807 | -67.73 | -9.68 | +1.160 |
| K | +457.378 | -50.78 | -52.15 | -125.771 |

Price guidance and funded discounts can make more offers compatible. A reward cannot create PV surplus or demand, and does not guarantee improvement for other seeds or inputs.

## Battery interpretation

Self-consumption-first batteries remove PV surplus before trading and reduce later demand. Compare absolute P2P energy alongside its changing denominator. E/F defer charging until after P2P, so their offered-surplus denominator includes PV subsequently stored. Compare raw PV surplus as well.

Initial stored battery energy is an exogenous inventory. Final stored energy can differ between strategies. Costs exclude inventory valuation, battery investment, degradation, taxes and network charges other than the modeled regulator fee.

## Accounting and limits

Internal payments transfer money between households. Fees transfer money to the regulator, and rewards transfer it back. Household net costs include these transfers. Household-plus-regulator net costs equal net external-grid payments. Every summary reports numerical energy and financial reconciliation errors.

The model uses copper-plate energy settlement without feeder limits, voltage, power flow, battery aging or strategic learning. A single deterministic day supports a demonstration, not a statistical claim. No improvement is forced.
