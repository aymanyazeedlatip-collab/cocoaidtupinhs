# Development Model Cards

Machine-readable cards are stored in `artifacts/model_cards/`.

## Production regression

- Algorithm: HistGradientBoostingRegressor
- Target: annual production in metric tons
- Split: grouped by synthetic farm ID
- Purpose: bounded correction to the transparent production equation
- Limitation: synthetic development relationships only

## Pest-risk classifier

- Algorithm: HistGradientBoostingClassifier
- Target: synthetic pest outcome
- Outputs: class probability used as one likelihood component in the Bayesian risk engine
- Metrics include accuracy, precision, recall, F1, ROC-AUC, Brier score, log loss, and confusion matrix
- Limitation: high synthetic performance is expected because labels follow encoded generation relationships

## Suitability regression

- Algorithm: RandomForestRegressor
- Target: synthetic suitability score
- Role: predictive development estimate blended with the transparent membership-function score
- Limitation: no independently verified land-suitability labels are bundled

All cards include this statement:

> The model learned the relationships encoded in the synthetic reference-based development dataset. Real-world validation remains required.
