# Model Artifact Runtime Contract

The three preserved artifacts were serialized with scikit-learn 1.9.0. Phase 1 pins:

```text
scikit-learn==1.9.0
```

The model registry now exposes:

- artifact filename;
- SHA-256 checksum;
- artifact version;
- ordered feature schema;
- model card;
- expected serialization runtime;
- installed runtime;
- exact or legacy-compatibility mode.

The Phase 1 build environment had scikit-learn 1.8.0 available, so complete tests were run in explicit `legacy_compatibility` mode. Predictions and all regression tests passed. A normal fresh Windows setup installs the pinned 1.9.0 dependency from `requirements.txt`; the local user should run `setup.bat` so the exact runtime can be verified on their machine.

`STRICT_MODEL_RUNTIME_COMPATIBILITY=true` can be used later to refuse model loading when the exact runtime is absent. It remains false during the controlled migration so the preserved prototype can still run in an audited compatibility environment.
