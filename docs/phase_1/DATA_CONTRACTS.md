# COCOAID v3 Data Contracts

Contract schema version: `3.0.0-draft.1`

All v3 contracts reject unknown fields, validate assignment, strip surrounding string whitespace, and expose JSON Schema through `/api/v2/contracts`.

## Canonical contracts

| Contract | Purpose |
| --- | --- |
| `FarmProfile` | Farm identity, pseudonymous owner link, location, area, and provenance |
| `FarmCell` | Spatial analysis unit with terrain, drainage, and canopy attributes |
| `TreeCohort` | Palm count grouped by state, variety, age, and cell |
| `FarmObservation` | Time-stamped measured or reported evidence |
| `ProductionRecord` | Observed product quantity over a valid period |
| `WeatherModelRun` | Immutable weather provider/model run and forecast validity window |
| `WeatherFeatureSet` | Versioned rolling and derived agricultural weather features |
| `ProductionForecast` | Raw ML, variety-adjusted, and posterior production outputs |
| `BayesianPosterior` | Posterior palm state, production interval, and risk probabilities |
| `PestAssessment` | Pest-specific probability, conditional loss, and expected loss |
| `IntercropCandidate` | Crop requirement reference record |
| `IntercropAssessment` | Cell-level decomposable suitability and conflict assessment |
| `RehabilitationPlan` | Evidence-linked, scheduled, costed farm actions |
| `AnalysisRun` | Multi-engine orchestration record |
| `RunProvenance` | Farm, weather, model, parameter, source, seed, and run lineage |

## Required semantic distinctions

- Numerical live forecasts cannot exceed 16 days.
- Longer horizons must use `climate_conditioned` data or forecast types.
- `predicted`, `suspected`, `farmer_reported`, `field_confirmed`, and `expert_confirmed` are separate evidence states.
- Pest `conditional_loss` and `expected_loss` are separate fields.
- Probabilities use the closed interval `0–1`.
- Normalized indices use `0–1`.
- Display suitability scores use `0–100`.
- Production records and forecasts use count, mass, or yield units only.
- Intercrop hard-constraint failures cap the score at 40 in the current contract.
- Rehabilitation action totals must match their cost components and remain within the declared budget.

## Canonical units

The unit registry is defined in `app/domain/units.py` and exposed by `/api/v2/units`.

Primary conventions:

| Quantity | Canonical unit |
| --- | --- |
| Farm area | hectare (`ha`) |
| Production mass | tonne (`t`) |
| Yield | tonne per hectare (`t/ha`) |
| Rainfall | millimeter (`mm`) |
| Temperature | degree Celsius (`degC`) |
| Wind speed | kilometer per hour (`km/h`) |
| Cost | Philippine peso (`PHP`) |
| Probability | `0–1` |

Only explicit registered conversions are permitted. Unsupported dimensional conversions fail instead of guessing.
