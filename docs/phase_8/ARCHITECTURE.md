# Phase 8 Architecture

`v3.rehabilitation` consumes a Phase 4 production forecast and optionally a Phase 5 Bayesian posterior, Phase 6 pest assessment run, and Phase 7 intercropping run. It does not duplicate those engines. It converts their versioned outputs plus explicit farm-cell context into evidence-linked triggers, candidate actions, and six comparable scenarios.

Flow:

```text
Production forecast + optional posterior + optional pest run + optional intercrop run
                                  +
                         farm-cell observations
                                  ↓
                       trigger detection
                                  ↓
                 evidence-safe action generation
                                  ↓
           cost, labor, recovery, and uncertainty ranges
                                  ↓
 six scenarios: no action / pest / fertility / replanting / intercrop / combined
                                  ↓
 budget and labor feasibility → expected-utility ranking → persisted plan
```

Predicted or suspected events cannot be marked as confirmed damage. Inferred pest risk can generate inspection and sanitation preparation, but pest treatment requires linked field- or expert-confirmed evidence.
