# Legacy Model Inventory

All three bundled models are preserved without retraining. Their model cards explicitly identify the training data as synthetic/reference-based, so they remain baseline prototype models pending field validation.

| Model | Artifact version | Data source | Features | Card metrics | SHA-256 |
| --- | --- | --- | --- | --- | --- |
| pest | pest-synthetic-1.0 | synthetic_reference_based | 13 | accuracy=0.9969, precision=0.9863, recall=1, f1=0.9931, roc_auc=1, brier=0.00309, log_loss=0.0165 | b78e99f6e7be8639… |
| production | production-synthetic-1.0 | synthetic_reference_based | 19 | mae=2.211, rmse=3.967, r2=0.5177 | a7c3b7182f0496a6… |
| suitability | suitability-synthetic-1.0 | synthetic_reference_based | 12 | mae=0.006199, rmse=0.008986, r2=0.9277 | 8f5ac092f0c0f559… |

## Compatibility risk

The artifacts were serialized with scikit-learn 1.9.0 while the current audit environment loaded scikit-learn 1.8.0. The test suite passes, but the resulting `InconsistentVersionWarning` is a release-blocking reproducibility risk for Phase 1.
