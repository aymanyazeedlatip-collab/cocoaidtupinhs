# Agricultural Weather Feature Adapter

Adapter version: `weather-features-1.0.0`

## Historical/reference features

- `rainfall_7d_mm`
- `rainfall_30d_mm`
- `rainfall_90d_mm`
- `moisture_balance_30d_mm`
- `moisture_balance_90d_mm`
- `consecutive_dry_days`
- `heat_stress_days_30d`
- `mean_solar_radiation_90d_mj_m2_day`
- `mean_relative_humidity_30d_percent`
- `mean_vpd_30d_kpa`
- `mean_soil_moisture_30d_fraction`

These features use provider `past_days` values and are explicitly marked `reference_only`. They support an initial adapter but do not substitute for field observations or a validated historical station dataset.

## Live forecast features

- `forecast_rainfall_16d_mm`
- `forecast_heat_stress_days_16d`
- `forecast_max_wind_gust_16d_kmh`

## Thresholds

- Dry day: precipitation below 1.0 mm/day
- Heat-stress day: maximum 2-m temperature above 33.0 °C

Thresholds are versioned implementation assumptions and must be calibrated during scientific validation. They are not presented as final PCA standards.

## Missing-data behavior

No weather feature is silently imputed. Incomplete windows receive `low_temporal_resolution`; completely absent variables receive `missing`. All output numbers remain finite and carry their derivation text.
