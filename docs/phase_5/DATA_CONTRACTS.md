# Phase 5 Data Contracts

The contract API version is `3.0.0-draft.5`.

## `PalmStateVector`

Requires non-negative integer counts for all seven palm states and `0–1` indices for soil fertility and soil water. The total palm count must be positive when stored as a posterior.

## `BayesianEvidenceObservation`

Supported evidence types and units:

| Evidence type | Accepted units |
|---|---|
| `harvest` | `kg`, `t` |
| `pest_prevalence` | `fraction`, `percent`, `probability` |
| `tree_mortality` | `count` |
| `storm_damage` | `fraction`, `percent`, `probability` |
| `rehabilitation_completion` | `fraction`, `percent`, `probability` |
| `actual_rainfall` | `mm` |

Evidence statuses are not interchangeable:

| Status | Bayesian behavior |
|---|---|
| `predicted` | Stored for traceability; not assimilated |
| `suspected` | Stored for traceability; not assimilated |
| `farmer_reported` | Assimilated with reduced reliability |
| `field_confirmed` | Assimilated with high reliability |
| `expert_confirmed` | Assimilated with full reliability |

## `BayesianSimulationRequest`

A request must supply exactly one state source:

1. `initial_state` for the first run; or
2. `prior_posterior_id` for a sequential update.

It also requires an existing `production_forecast_id`, an aware baseline datetime, a horizon of 1–60 months, 100–5,000 particles, a stored seed, and unique evidence-observation IDs.

## `BayesianPosterior`

The output preserves:

- median farm state;
- 5th–95th percentile intervals for every state and soil index;
- posterior parameter summaries;
- production 5th percentile, median, and 95th percentile;
- probability of decline;
- probability of recovery;
- probability of tree mortality;
- probability of pest outbreak;
- main uncertainty sources;
- linked evidence IDs;
- model, parameter, farm-data, weather, seed, and simulation-count provenance.
