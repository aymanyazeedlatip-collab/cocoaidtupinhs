# Phase 6 Architecture

Phase 6 introduces an executable PCA pest-specific inference layer between the weather/production/Bayesian core and later intercropping and rehabilitation engines.

```text
PCA pest profiles and rules
          +
Phase 3 weather feature set
          +
Phase 4 production forecast
          +
Optional Phase 5 posterior
          +
Farm context, symptoms, observations, nearby confirmed cases
                         ↓
              Pest Inference Engine
                         ↓
Probability + severity + exposed palms
                         ↓
Conditional loss and expected loss
                         ↓
Inspection timing, PCA actions, quarantine warning, audit trail
```

The engine supports exactly five PCA-backed profiles: coconut scale insect, coconut rhinoceros beetle, coconut leaf beetle, Asiatic palm weevil, and coconut bud and nut rot. The legacy red-palm-weevil profile remains separate and is not used by the v3 engine.

The inference engine does not call an LLM, does not prescribe pesticide dosage, and does not treat model-predicted or suspected observations as confirmed evidence.
