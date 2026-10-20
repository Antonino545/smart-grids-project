# Experiment discussion

These are model outputs for the recorded inputs and assumptions, not evidence of real-world performance.

| Scenario | P2P kWh | P2P share % | Imports kWh | Exports kWh | Household net cost EUR |
|---|---:|---:|---:|---:|---:|
| A | 8.935 | 0.626 | 513.209 | 1412.661 | 69.203 |
| B | 18.656 | 1.308 | 506.723 | 1406.176 | 86.466 |
| C | 12.822 | 0.683 | 840.096 | 1861.174 | 140.358 |
| D | 26.766 | 1.425 | 828.587 | 1849.665 | 163.938 |
| E | 10.709 | 0.570 | 511.854 | 1411.328 | 68.877 |
| F | 21.801 | 1.161 | 503.578 | 1403.052 | 85.615 |

## Regulation comparisons
- B versus A: regulation increased P2P energy (difference +9.721 kWh).
- D versus C: regulation increased P2P energy (difference +13.943 kWh).
- F versus E: regulation increased P2P energy (difference +11.091 kWh).

Price guidance and funded discounts can make more offers compatible. A reward cannot create PV surplus or demand, and does not guarantee improvement for other seeds or inputs.

## Battery interpretation

Self-consumption-first batteries remove PV surplus before trading and reduce later demand. Compare absolute P2P energy alongside its changing denominator. E/F defer charging until after P2P, so their offered-surplus denominator includes PV subsequently stored. Compare raw PV surplus as well.

Initial stored battery energy is an exogenous inventory. Final stored energy can differ between strategies. Costs exclude inventory valuation, battery investment, degradation, taxes and network charges other than the modeled regulator fee.

## Accounting and limits

Internal payments transfer money between households. Fees transfer money to the regulator, and rewards transfer it back. Household net costs include these transfers. Household-plus-regulator net costs equal net external-grid payments. Every summary reports numerical energy and financial reconciliation errors.

The model uses copper-plate energy settlement without feeder limits, voltage, power flow, battery aging or strategic learning. A single deterministic day supports a demonstration, not a statistical claim. No improvement is forced.
