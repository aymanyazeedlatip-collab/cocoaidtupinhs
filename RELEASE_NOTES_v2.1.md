# COCO-AID v2.1 Release Notes

This release focuses on four connected improvements:

1. **Smooth farm weather heatmap** — climate-conditioned rainfall is rendered as a continuous transparent-blue-yellow-red field using bilinear interpolation and visual smoothing. The map no longer exposes the coarse model cells as large squares.
2. **Weather-responsive product categories** — Coconut Mature and Coconut Young now use distinct response equations for moisture, humidity, temperature, heat, wind, excess rain, pest pressure, farm condition, and extreme-event severity. Both remain mathematically conserved within total Coconut (w/ husk) production.
3. **Farm-health decision support** — Bayesian pest posterior, land suitability, and farm condition are emphasized through donut charts. Eight illustrated pest-specific assessments provide 0-100 outbreak-priority scores, mathematical drivers, and inspection-oriented recommendations.
4. **Formal reporting** — PDF and DOCX reports use formal serif styling, black report text, corrected numerical formatting, critical-weather heatmap snapshots, pest-specific findings, weather-responsive product equations, and severity/duration-consistent hazard losses.

## Interpretation

Long-term weather fields are climate-conditioned scenario paths, not exact forecasts of future clouds, rainfall, heat waves, or storm dates. Pest-specific values are inspection priorities rather than laboratory identifications. Farm-scale validation remains necessary.

## Verification

- 64 automated tests pass.
- Python source compilation passes.
- Main and embedded Weather GIS JavaScript syntax checks pass.
- Installation verification passes.
- PDF and DOCX reports were generated, rendered, and visually inspected page by page.
