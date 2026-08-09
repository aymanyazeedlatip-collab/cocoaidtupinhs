# Phase 7 Scoring Model

The weighted components are light, temperature, rainfall/water, soil pH, drainage, available space, nitrogen, management feasibility, and slope. Their weighted geometric mean prevents several favorable factors from fully hiding a severe limiting factor.

The base score is reduced by bounded coconut-competition and pest-conflict penalties. Hard light or slope failures cap the final score at 40.

PCA source support is strongest for crop light bands and canopy light-transmission rows. Temperature, rainfall, soil, drainage, resource-demand, component-weight, and penalty values are explicit low-confidence development assumptions stored under `intercrop-suitability-parameters-1.0.0` and `intercrop-requirements-1.0.0`.

Cacao and coffee economic outputs are gross-revenue scenarios based on sanitized aggregate profiles. They are scaled by cell area and suitability and must not be interpreted as net profit, ROI, or guaranteed future income.
