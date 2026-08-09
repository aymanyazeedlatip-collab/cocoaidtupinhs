# Phase 7 Architecture

The Phase 7 intercropping engine is an executable, spatial evidence-scoring module. It consumes a stored Phase 4 production forecast, the associated Phase 3 weather feature set, optional Phase 5 posterior provenance, optional Phase 6 pest probabilities, PCA crop-light bands, PCA canopy-transmission rows, provisional non-light crop requirements, and sanitized cacao/coffee gross-revenue profiles.

Processing order:

```text
Production forecast and weather feature set
                 +
Cell canopy, soil, slope, space, and management context
                 +
PCA light bands and canopy table
                 +
Optional Phase 6 pest run
                 +
Optional aggregate economic profile
                         ↓
Canopy-light interpolation
                         ↓
Decomposable component scores
                         ↓
Competition and pest-conflict penalties
                         ↓
Hard-constraint cap
                         ↓
Candidate-by-cell suitability and planting guidance
```

The engine does not train or claim a supervised intercropping model. UI code is not involved in the scientific calculations.
