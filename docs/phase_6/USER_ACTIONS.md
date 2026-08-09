# Phase 6 User Actions

This checklist is self-contained. You do not need to return to an earlier phase document.

## 1. Install and test

1. Keep the Phase 5 folder and ZIP as a backup.
2. Extract the Phase 6 ZIP into a new folder.
3. Do not copy the Phase 5 `.venv` directory.
4. Connect to the internet and run `setup.bat`.
5. Run `test.bat` and confirm `210 tests across 62 fully isolated test-file processes`.
6. Run `run.bat`.
7. Open `http://127.0.0.1:8000/api/v2/health` and confirm contract `3.0.0-draft.6` and migrations 1–6 are applied.
8. Open `http://127.0.0.1:8000/api/v2/pests/status` and confirm `v3.pest_inference` version `1.0.0` is available.

## 2. Create the required weather feature set

Open `http://127.0.0.1:8000/docs`, expand `POST /api/v2/weather/assimilate`, select **Try it out**, and use:

```json
{
  "latitude": 6.334,
  "longitude": 124.952,
  "model": "auto",
  "forecast_days": 16,
  "history_days": 90,
  "force_refresh": false
}
```

Copy `feature_set.id` from the response. This is the `weather_feature_set_id` used in the next request.

## 3. Create the required production forecast

Expand `POST /api/v2/production/forecast` and replace `PASTE-WEATHER-FEATURE-SET-ID`:

```json
{
  "farm_id": "550e8400-e29b-41d4-a716-446655440000",
  "farm_data_version": "phase6-manual-test-farm-1",
  "weather_feature_set_id": "PASTE-WEATHER-FEATURE-SET-ID",
  "farm_area_hectares": 5,
  "productive_trees": 320,
  "aging_trees": 40,
  "stressed_trees": 20,
  "infested_trees": 5,
  "recovering_trees": 10,
  "soil_ph": 6.1,
  "nitrogen_index": 0.65,
  "phosphorus_index": 0.6,
  "potassium_index": 0.7,
  "suitability_score": 0.78,
  "pest_probability": 0.12,
  "variety_id": "agdt",
  "variety_class": "Unknown",
  "intervention": "none",
  "baseline_annual_production_tons": 25,
  "young_nut_share": 0.03
}
```

Copy `output.forecast.production_forecast_id`.

## 4. Record one field pest observation

Expand `POST /api/v2/pests/observations`. Replace the production forecast ID and use:

```json
{
  "farm_id": "550e8400-e29b-41d4-a716-446655440000",
  "production_forecast_id": "PASTE-PRODUCTION-FORECAST-ID",
  "pest_profile_id": "coconut-scale-insect",
  "factor_code": "scale_colonies",
  "evidence_status": "field_confirmed",
  "observed_at": "2026-08-03T18:00:00+08:00",
  "value": true,
  "unit": "fraction",
  "prevalence_fraction": 0.15,
  "latitude": 6.334,
  "longitude": 124.952,
  "source_label": "Manual field inspection",
  "notes": "Visible scale colonies observed on sampled leaflets."
}
```

Copy `observation_id`. The response should also report `bayesian_link_created: true` because a prevalence fraction was supplied.

## 5. Run the Phase 6 pest assessment

Expand `POST /api/v2/pests/assess`. Replace the production forecast ID and observation ID:

```json
{
  "farm_id": "550e8400-e29b-41d4-a716-446655440000",
  "production_forecast_id": "PASTE-PRODUCTION-FORECAST-ID",
  "posterior_id": null,
  "pest_profile_ids": [
    "bud-nut-rot",
    "coconut-leaf-beetle",
    "rhinoceros-beetle",
    "asiatic-palm-weevil",
    "coconut-scale-insect"
  ],
  "assessed_at": "2026-08-03T18:10:00+08:00",
  "context": {
    "total_palms": 425,
    "young_palms": 25,
    "healthy_bearing_palms": 320,
    "aging_palms": 40,
    "stressed_palms": 20,
    "infested_or_diseased_palms": 5,
    "rehabilitating_palms": 10,
    "dead_palms": 5,
    "mean_palm_age_years": 18,
    "maintenance_quality": 0.55,
    "sanitation_quality": 0.55,
    "drainage_quality": 0.6,
    "waterlogging": false,
    "natural_enemies_present": false,
    "decaying_organic_breeding_material": false,
    "fresh_palm_wounds": false,
    "storm_damage": false,
    "symptom_codes": ["scale_colonies_on_leaflets"]
  },
  "observation_ids": ["PASTE-OBSERVATION-ID"],
  "nearby_confirmed_cases": [],
  "farm_data_version": "phase6-manual-test-farm-1"
}
```

Confirm the response contains five assessments and, for each profile:

- `outbreak_probability`
- `risk_class`
- `conditional_loss`
- `expected_loss`
- `evidence_contributions`
- `symptoms_to_inspect`
- `management_actions`
- `recommended_inspection_at`

`expected_loss` must equal `outbreak_probability × conditional_loss` and must not exceed `conditional_loss`.

## 6. Optional Bayesian posterior baseline

Phase 6 works without a Phase 5 posterior. To use a posterior-adjusted production baseline, run `POST /api/v2/bayesian/simulate` with:

```json
{
  "production_forecast_id": "PASTE-PRODUCTION-FORECAST-ID",
  "initial_state": {
    "young": 25,
    "healthy_bearing": 320,
    "aging": 40,
    "stressed": 20,
    "infested_or_diseased": 5,
    "rehabilitating": 10,
    "dead": 5,
    "soil_fertility_index": 0.65,
    "soil_water_index": 0.6
  },
  "baseline_state_date": "2026-08-03T18:00:00+08:00",
  "horizon_months": 12,
  "particle_count": 300,
  "random_seed": 20260803,
  "intervention": "none",
  "evidence_observation_ids": [],
  "farm_data_version": "phase6-manual-test-farm-1"
}
```

Copy `output.posterior.posterior_id` and replace `"posterior_id": null` in the pest assessment with that ID.

## 7. Privacy and evidence rules

Do not publicly share:

- `data/coco_aid.sqlite3`
- `backups/`
- `data_sources/raw/farmers/`
- `data_sources/raw/intercropping/`

Use `predicted` or `suspected` for unconfirmed model or visual indications. Only use `field_confirmed` or `expert_confirmed` for genuine observations. Phase 6 intentionally does not merge the PCA Asiatic palm weevil profile with the legacy red palm weevil profile.
