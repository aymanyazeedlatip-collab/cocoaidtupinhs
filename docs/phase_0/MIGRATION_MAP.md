# Legacy-to-v3 Migration Map

## Strategy

The v3 architecture will be introduced beside the v2.11 modules. Legacy endpoints remain available until equivalent v3 services pass regression and scientific acceptance tests.

## Storage migration

| Legacy table/field | v3 target | Migration treatment |
| --- | --- | --- |
| `farms.payload` | `farms`, `farm_boundaries`, `tree_cohorts`, `farm_management_profiles` | Parse and normalize; preserve original JSON snapshot and source version. |
| `analyses.input_payload` | `analysis_runs`, `analysis_inputs` | Assign one run identifier and immutable input snapshot. |
| `analyses.result_payload` | Engine-specific result tables | Split production, Bayesian, pest, suitability, intercrop, rehabilitation, and scenario outputs. |
| `analyses.metadata_payload` | `run_provenance`, `model_versions`, `parameter_versions`, `source_versions` | Normalize lineage and maintain exact original metadata. |
| `saved_forecasts.forecast_payload` | `weather_model_runs`, `weather_features`, `production_forecasts`, `climate_scenarios` | Separate numerical forecast from climate-conditioned simulation. |
| `reports.filepath` | `reports`, `report_artifacts`, `report_run_links` | Add hash, template version, and source analysis-run relation. |

## Code migration

| Legacy component | v3 bounded context | First action |
| --- | --- | --- |
| `app/api/routes.py` | `app/api/v2/*` and later `app/api/v3/*` | Split handlers without changing route contracts. |
| `app/storage/database.py` | repositories plus migration framework | Introduce connection/session abstraction and versioned migrations. |
| `app/models/registry.py` | model registry and inference adapters | Pin artifact compatibility, hashes, feature schemas, and status reporting. |
| `app/weather/providers.py` | weather ingestion service | Save immutable provider runs and enforce forecast-horizon semantics. |
| `app/simulation/farm_site_forecast.py` | production, climate, hazard, and spatial services | Extract one responsibility at a time under characterization tests. |
| `app/simulation/engine.py` | Bayesian farm-state engine | Preserve legacy simulator as `legacy_v211`; implement observation-aware v3 engine separately. |
| `app/math/pest_specific.py` | pest-profile registry and inference engine | Create independent pest contracts and provenance-linked rules. |
| `app/gis/analysis.py` | spatial assessment and rehabilitation services | Separate cell generation, scoring, action planning, and map serialization. |
| `app/static/app.js` | feature modules and shared state/services | Extract API client and application state before rebuilding pages. |
| `app/static/styles.css` | design tokens, components, and feature styles | Freeze visual baseline, then modularize without changing behavior. |

## Compatibility controls

- Feature flags select legacy or v3 engines.
- Every v3 result stores the corresponding legacy result during shadow comparison.
- Identical fixture, seed, model hash, parameter version, and weather run must reproduce the same result.
- A legacy route is retired only after contract, regression, performance, and scientific review gates pass.
