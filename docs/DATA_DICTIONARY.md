# Data Dictionary

The machine-readable version is `DATA_DICTIONARY.csv`. All bundled farm-year records are synthetic reference-based.

| Field | Type | Description |
|---|---|---|
| `record_id` | object | Unique synthetic farm-year record identifier |
| `farm_id` | object | Anonymous synthetic farm identifier |
| `year` | int64 | Observation year |
| `region` | object | Philippine administrative region label used in generation |
| `province` | object | Province label used in generation |
| `latitude` | float64 | Synthetic farm latitude in decimal degrees |
| `longitude` | float64 | Synthetic farm longitude in decimal degrees |
| `elevation_m` | float64 | Elevation above mean sea level in metres |
| `slope_degrees` | float64 | Terrain slope in degrees |
| `farm_area_hectares` | float64 | Farm area in hectares |
| `tree_density_per_hectare` | float64 | Coconut planting positions per hectare |
| `total_trees` | int64 | Total tree states/planting positions |
| `young_trees` | int64 | Young or newly replanted palms |
| `productive_trees` | int64 | Productive palms |
| `aging_trees` | int64 | Aging or senescent palms |
| `stressed_trees` | int64 | Environmentally stressed palms |
| `infested_trees` | int64 | Infested or diseased palms |
| `recovering_trees` | int64 | Recovering or rehabilitating palms |
| `dead_trees` | int64 | Dead palms or vacant positions |
| `average_tree_age` | float64 | Average palm age in years |
| `variety` | object | Tall, Dwarf, or Hybrid development category |
| `soil_ph` | float64 | Soil pH |
| `nitrogen_index` | float64 | Normalized nitrogen availability index |
| `phosphorus_index` | float64 | Normalized phosphorus availability index |
| `potassium_index` | float64 | Normalized potassium availability index |
| `drainage_index` | float64 | Normalized drainage suitability proxy |
| `annual_rainfall_mm` | float64 | Annual rainfall in millimetres |
| `mean_temperature_c` | float64 | Annual mean temperature in degrees Celsius |
| `relative_humidity_percent` | float64 | Mean relative humidity percent |
| `drought_exposure` | float64 | Normalized drought exposure index |
| `typhoon_exposure` | float64 | Normalized typhoon exposure proxy |
| `weather_event` | object | Generated annual event category |
| `weather_severity` | float64 | Normalized event severity |
| `intervention` | object | Synthetic management intervention |
| `pest_control` | int64 | Pest-control indicator |
| `soil_rehabilitation` | int64 | Soil-rehabilitation indicator |
| `replanting` | int64 | Replanting indicator |
| `yellowing` | int64 | Yellowing symptom indicator |
| `crown_decline` | int64 | Crown-decline symptom indicator |
| `frond_cuts` | int64 | Frond-cut symptom indicator |
| `visible_scale_insects` | int64 | Visible scale-insect indicator |
| `rhinoceros_beetle_damage` | int64 | Rhinoceros-beetle damage indicator |
| `premature_nut_fall` | int64 | Premature nut-fall indicator |
| `nearby_reports` | int64 | Nearby pest-report indicator |
| `symptom_severity` | int64 | Ordinal symptom severity 0–3 |
| `pest_probability` | float64 | Synthetic generative pest probability |
| `pest_outcome` | int64 | Synthetic binary pest outcome |
| `suitability_score` | float64 | Synthetic target suitability score 0–1 |
| `suitability_class` | int64 | Synthetic suitability class |
| `annual_production_tons` | float64 | Synthetic annual coconut production in metric tons |
| `yield_tons_per_hectare` | float64 | Synthetic annual yield per hectare |
| `replanting_survival` | float64 | Synthetic replanting survival outcome |
| `rehabilitation_success` | int64 | Synthetic rehabilitation success outcome |
| `data_source_type` | object | Data provenance category |
| `is_synthetic` | bool | True for generated records |
| `generation_version` | object | Generator version |
| `generation_seed` | int64 | Reproducibility seed |
| `reference_group` | object | Reference grouping label |
| `created_at` | object | UTC creation timestamp |
| `quality_flag` | object | Development-use quality classification |

## Phase 3 weather assimilation records

| Record/field | Type | Description |
|---|---|---|
| `weather_model_runs` | table | Immutable provider retrieval with location, requested horizons, timestamps, payload hash, units, quality flags, and provider metadata |
| `provider_run_at` | datetime or null | Provider initialization time when explicitly exposed; null for seamless model output without one authoritative timestamp |
| `provider_run_time_basis` | text | Explanation of how or why provider initialization time is represented |
| `weather_values` | table | Long-form current, historical-reference, and forecast values by valid time, variable, resolution, and unit |
| `period_kind` | enum | `historical`, `current`, or `forecast` |
| `weather_feature_sets` | table | Versioned collection of agricultural weather features for a weather run and optional farm |
| `feature_adapter_version` | text | Exact feature-engineering implementation version |
| `weather_features` | table | Feature value, unit, aggregation window, derivation, and quality flags |
