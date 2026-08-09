# Official PSA Coconut-Production Data

## Source

- Agency: Philippine Statistics Authority (PSA)
- Table: `2E4EVCP1`
- Title: *Non-Food and Industrial Crops: Volume of Production, by Region, Province, Quarter, and Semester, 2010-2026*
- Unit: metric tons
- Source workbook: `data/source/COCONUT_PRODUCTION_ALL_PROVINCES_2010_2026_PSA.xlsx`
- Latest update shown in the workbook: 2026-06-04

## Product groups

- Coconut (w/ husk)
- Coconut Mature
- Coconut Young

The mature and young series are treated as components of the with-husk total, subject to source rounding.

## Coverage and status

The workbook supplies provincial, regional, and national rows. Completed annual observations through 2025 are tagged `official_psa`. The workbook note identifies Quarter 1 2026 as preliminary. Annual 2026 and unavailable cells are estimated from available quarters, location-specific historical seasonal shares, and annual interpolation/extrapolation. Those values are tagged `estimated_gap` or `estimated_from_official_quarters` and are never represented by the backend as completed official annual observations.

## Processed files

- `psa_coconut_production_tidy.csv` — product/location/year/period/value/status records
- `psa_coconut_production_annual.csv` — annual product totals and status
- `psa_province_profiles.json` — 88 province profiles plus region/national fallbacks
- `psa_metadata.json` — source, coverage, update date, unit, and estimation method

## Uses inside COCO-AID

- Province selector and official history graph
- 2025 reference values and 2026 estimates
- Province-specific quarterly seasonality
- Mature/young share calibration
- Three-product weekly and annual forecast visualization
- Full-analysis provenance and PDF/DOCX report sections

## Uses that are not scientifically justified

Provincial aggregate production cannot directly determine the yield of an individual farm. COCO-AID therefore does not automatically replace a farmer's production input with the provincial total. Farm forecasts still require farm area, tree states, production history, soil, management, weather, and model assumptions.
