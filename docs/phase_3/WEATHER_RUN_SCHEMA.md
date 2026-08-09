# Weather Run Storage Schema

Migration 3 adds four normalized tables.

## `weather_model_runs`

One immutable provider retrieval. It records provider/model, location, requested history and forecast horizons, retrieval time, provider initialization time when exposed, validity range, raw-payload SHA-256, units, quality flags, provider metadata, and stale state.

The Open-Meteo seamless/automatic model endpoint does not expose one authoritative initialization timestamp. `provider_run_at` is therefore nullable and `provider_run_time_basis` records why.

## `weather_values`

Long-form values keyed by run, valid time, resolution, and variable. `period_kind` is one of:

- `historical`
- `current`
- `forecast`

Historical Forecast API `past_days` values are marked `reference_only`.

## `weather_feature_sets`

One versioned agricultural feature adapter output per weather run, farm, and adapter version.

## `weather_features`

Long-form feature values with unit, aggregation window, derivation, and quality flags.

## Reproducibility fields

A stored result can be reconstructed using:

- Weather run ID
- Provider payload hash
- Provider/model identifier
- Retrieval and validity timestamps
- Feature-adapter version
- Farm ID when provided
- Stored derivation and quality flags
