# Experiment discussion

These are model outputs for the recorded inputs and assumptions, not evidence of real-world performance.

| Scenario | P2P kWh | P2P share % | Imports kWh | Exports kWh | Household net cost EUR |
|---|---:|---:|---:|---:|---:|
| A | 863.982 | 13.985 | 18268.301 | 4495.218 | 5210.777 |
| B | 2858.451 | 46.269 | 16721.153 | 2948.070 | 4978.985 |
| C | 1047.066 | 14.188 | 19029.806 | 5440.493 | 5382.512 |
| D | 3523.217 | 47.741 | 17074.078 | 3484.765 | 5048.262 |
| E | 1030.768 | 13.967 | 18215.841 | 4481.092 | 5195.887 |
| F | 3473.971 | 47.074 | 16447.048 | 2846.534 | 4886.779 |

## Regulation comparisons
- B versus A: regulation increased P2P energy (difference +1994.469 kWh).
- D versus C: regulation increased P2P energy (difference +2476.151 kWh).
- F versus E: regulation increased P2P energy (difference +2443.203 kWh).

Price guidance and funded discounts can make more offers compatible. A reward cannot create PV surplus or demand, and does not guarantee improvement for other seeds or inputs.

## Battery interpretation

Self-consumption-first batteries remove PV surplus before trading and reduce later demand. Compare absolute P2P energy alongside its changing denominator. E/F defer charging until after P2P, so their offered-surplus denominator includes PV subsequently stored. Compare raw PV surplus as well.

Initial stored battery energy is an exogenous inventory. Final stored energy can differ between strategies. Costs exclude inventory valuation, battery investment, degradation, taxes and network charges other than the modeled regulator fee.

## Accounting and limits

Internal payments transfer money between households. Fees transfer money to the regulator, and rewards transfer it back. Household net costs include these transfers. Household-plus-regulator net costs equal net external-grid payments. Every summary reports numerical energy and financial reconciliation errors.

The model uses copper-plate energy settlement without feeder limits, voltage, power flow, battery aging or strategic learning. A single deterministic day supports a demonstration, not a statistical claim. No improvement is forced.
