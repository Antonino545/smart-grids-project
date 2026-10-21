# Experiment discussion

These are model outputs for the recorded inputs and assumptions, not evidence of real-world performance.

| Scenario | P2P kWh | P2P share % | Imports kWh | Exports kWh | Household net cost EUR |
|---|---:|---:|---:|---:|---:|
| A | 254.554 | 4.120 | 7735.928 | 5708.808 | 1978.250 |
| B | 706.991 | 11.444 | 7421.821 | 5394.701 | 2016.890 |
| C | 362.877 | 4.917 | 8656.509 | 6813.158 | 2188.163 |
| D | 1051.853 | 14.253 | 8091.691 | 6248.340 | 2174.970 |
| E | 334.444 | 4.532 | 7727.116 | 5726.260 | 1974.559 |
| F | 903.547 | 12.243 | 7287.775 | 5289.487 | 1976.665 |

## Regulation comparisons
- B versus A: regulation increased P2P energy (difference +452.438 kWh).
- D versus C: regulation increased P2P energy (difference +688.976 kWh).
- F versus E: regulation increased P2P energy (difference +569.103 kWh).

Price guidance and funded discounts can make more offers compatible. A reward cannot create PV surplus or demand, and does not guarantee improvement for other seeds or inputs.

## Battery interpretation

Self-consumption-first batteries remove PV surplus before trading and reduce later demand. Compare absolute P2P energy alongside its changing denominator. E/F defer charging until after P2P, so their offered-surplus denominator includes PV subsequently stored. Compare raw PV surplus as well.

Initial stored battery energy is an exogenous inventory. Final stored energy can differ between strategies. Costs exclude inventory valuation, battery investment, degradation, taxes and network charges other than the modeled regulator fee.

## Accounting and limits

Internal payments transfer money between households. Fees transfer money to the regulator, and rewards transfer it back. Household net costs include these transfers. Household-plus-regulator net costs equal net external-grid payments. Every summary reports numerical energy and financial reconciliation errors.

The model uses copper-plate energy settlement without feeder limits, voltage, power flow, battery aging or strategic learning. A single deterministic day supports a demonstration, not a statistical claim. No improvement is forced.
