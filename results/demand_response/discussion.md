# Experiment discussion

These are model outputs for the recorded inputs and assumptions, not evidence of real-world performance.

| Scenario | P2P kWh | P2P share % | Imports kWh | Exports kWh | Household net cost EUR |
|---|---:|---:|---:|---:|---:|
| A | 847.031 | 14.543 | 17940.020 | 4166.938 | 5131.990 |
| B | 2699.393 | 46.348 | 16529.847 | 2756.764 | 4932.426 |
| C | 1004.087 | 14.291 | 18722.739 | 5133.426 | 5308.816 |
| D | 3357.257 | 47.783 | 16911.935 | 3322.622 | 5009.424 |
| E | 993.673 | 14.143 | 17901.293 | 4166.097 | 5120.422 |
| F | 3306.066 | 47.054 | 16271.948 | 2673.147 | 4844.525 |

## Regulation comparisons
- B versus A: regulation increased P2P energy (difference +1852.362 kWh).
- D versus C: regulation increased P2P energy (difference +2353.170 kWh).
- F versus E: regulation increased P2P energy (difference +2312.393 kWh).

Price guidance and funded discounts can make more offers compatible. A reward cannot create PV surplus or demand, and does not guarantee improvement for other seeds or inputs.

## Battery interpretation

Self-consumption-first batteries remove PV surplus before trading and reduce later demand. Compare absolute P2P energy alongside its changing denominator. E/F defer charging until after P2P, so their offered-surplus denominator includes PV subsequently stored. Compare raw PV surplus as well.

Initial stored battery energy is an exogenous inventory. Final stored energy can differ between strategies. Costs exclude inventory valuation, battery investment, degradation, taxes and network charges other than the modeled regulator fee.

## Accounting and limits

Internal payments transfer money between households. Fees transfer money to the regulator, and rewards transfer it back. Household net costs include these transfers. Household-plus-regulator net costs equal net external-grid payments. Every summary reports numerical energy and financial reconciliation errors.

The model uses copper-plate energy settlement without feeder limits, voltage, power flow, battery aging or strategic learning. A single deterministic day supports a demonstration, not a statistical claim. No improvement is forced.
