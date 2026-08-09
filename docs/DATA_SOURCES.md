# Data Sources

## Official agricultural statistics

**Philippine Statistics Authority — table 2E4EVCP1**

Used for provincial/region/national production history, product shares, and seasonal calibration. See `OFFICIAL_PSA_DATA.md` for status and estimation rules.

## Live and short-term weather

- Open-Meteo: deterministic forecast fields
- RainViewer: radar timeline and tiles
- NASA GIBS: satellite-reference imagery
- GDACS: supplemental cyclone information
- PAGASA: official Philippine warning reference
- OpenStreetMap: basemap

Provider data are cached and clearly typed. Cached data can be marked stale. Provider failure does not become fabricated live weather.

## Long-term climate

The default compact projection layer follows SSP and climate-period conventions for immediate local demonstration. Replace it with processed NASA NEX-GDDP-CMIP6, WorldClim CMIP6, or another validated climate product for research deployment.

## Farm and model inputs

Tree states, production, management, symptoms, and soil values are supplied by the user or estimated by the development framework. The initial ML artifacts require validation using real longitudinal farm records.
