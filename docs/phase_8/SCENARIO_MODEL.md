# Scenario and Utility Model

Phase 8 always evaluates six scenarios:

1. `no_action`
2. `pest_management`
3. `fertilization`
4. `replanting`
5. `intercropping`
6. `combined_rehabilitation`

Each scenario filters the generated action catalog, totals materials, labor, other cost, and person-days, then checks budget and labor feasibility. `no_action` is always feasible.

Production remains an interval. Scenario effects reduce residual severe-loss probability and add a bounded recovery assumption. Intercrop gross revenue is used only when a linked Phase 7 aggregate economic profile exists. Comparative expected utility is:

```text
coconut production value
+ discounted intercrop gross revenue
- intervention cost
- risk-aversion penalty
```

The utility is a ranking instrument, not guaranteed profit, ROI, or a causal estimate.
