# Frozen Production Feature Adapter

**Adapter version:** `production-feature-adapter-1.0.0`

The retained artifact requires this exact order:

1. `farm_area_hectares`
2. `productive_trees`
3. `aging_trees`
4. `stressed_trees`
5. `infested_trees`
6. `recovering_trees`
7. `annual_rainfall_mm`
8. `mean_temperature_c`
9. `relative_humidity_percent`
10. `drought_exposure`
11. `weather_severity`
12. `soil_ph`
13. `nitrogen_index`
14. `phosphorus_index`
15. `potassium_index`
16. `suitability_score`
17. `pest_probability`
18. `variety`
19. `intervention`

The adapter verifies this list against the model artifact before every execution. The ordered payload is SHA-256 hashed and stored.

## Weather derivations

- Annual rainfall is annualized from the Phase 3 90-day rainfall window, with a flagged 30-day fallback.
- Mean temperature is calculated from archived daily mean values or daily maximum/minimum midpoints.
- Drought exposure is derived from consecutive dry days and moisture deficit.
- Weather severity combines drought, forecast heat days, forecast gusts, and moisture deficit.

Archived Open-Meteo `past_days` values are reference-only forecast-history values, not station observations. The adapter preserves that limitation in quality flags and provenance.

A named PCA variety is resolved before feature adaptation, ensuring that a dwarf or hybrid reference is not incorrectly sent to the retained model as Tall.
