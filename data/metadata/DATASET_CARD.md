# COCO-AID Synthetic Development Dataset Card

## Dataset

`data/synthetic/coconut_farm_years.csv`

## Purpose

This dataset exists to test the COCO-AID mathematical framework, backend, model-training pipeline, simulation coupling, API, and interface while real longitudinal farm data are being collected.

## Generation

- Generator: `scripts/generate_data.py`
- Version: `agri-synthetic-0.9`
- Default seed: `20260719`
- Default size: 360 synthetic farms × 8 years
- Data-source type: `synthetic_reference_based`

Variables are generated with connected relationships. Examples include elevation effects on temperature, correlated nutrient indices, age-related decline, humidity/rainfall effects on pest probability, event damage to tree states and yield, replanting delay, and management effects.

## Intended use

- Development and automated testing
- Demonstrating reproducible feature engineering
- Training provisional development models
- Verifying the Bayesian and Monte Carlo workflow
- Preparing schemas before real data arrive

## Prohibited claims

- Real Philippine farm observations
- Real-world predictive accuracy
- Official production or pest forecasts
- Laboratory-confirmed soil or oil-content data
- A replacement for independent validation

## Quality checks

Generation produces `data/metadata/GENERATION_REPORT.json`, which verifies provenance fields, nonnegative rainfall, valid probabilities, and tree-state conservation.

## Limitations

The data encode assumptions. A model can perform extremely well by learning those assumptions. Performance must be re-evaluated using real, independently collected farm records.
