# Hybrid Weather and Farm Production Forecast

## Short-term segment

When live provider access is enabled and the current forecast horizon overlaps the selected start date, COCO-AID requests one cached multi-variable regional cube. It aggregates provider precipitation, temperature, humidity, clouds, pressure, wind speed, and wind direction to the farm and map.

## Long-term segment

After the provider horizon, COCO-AID uses a climate-conditioned stochastic path. Weekly map fields after this transition are generated visualizations linked to the farm's simulated rainfall and atmospheric conditions. They are not future radar or exact cloud forecasts.

## Weekly production

The farm simulator first produces annual stochastic farm-state and production outcomes. Daily weights reflect seasonality, weather stress, and event effects; these are then aggregated into weekly production equivalents. The selected province's PSA quarter shares and mature/young composition split the total into:

- Coconut (w/ husk)
- Coconut Mature
- Coconut Young

Mature plus Young is conserved to the with-husk total after allocation. Annual product totals are derived from daily allocations rather than week-start grouping, preventing cross-year weeks from being assigned to the wrong year. The selected start year is labeled partial when it begins after January 1.

## Synchronized visualization

One weekly timeline controls:

- TV-style rain field and wind arrows
- Farm condition and production cards
- Production chart
- Rainfall and temperature chart
- Humidity/cloud/wind/pressure chart
- Condition and pest chart
- Official-history marker
- Extreme-weather timeline

## Interpretation

The short-term segment is a numerical forecast. The long-term segment is a plausible projection. Weekly production is a model allocation, not a guaranteed exact-week harvest.
