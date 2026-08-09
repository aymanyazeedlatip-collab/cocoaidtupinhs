# Pest Inference Model

## Evidence calculation

The engine starts from a versioned development inspection prior and updates log-odds using matched PCA evidence rules. PCA materials provide qualitative risk factors, but not calibrated likelihood ratios. Therefore the numerical likelihood ratios are explicit experimental parameters in `pest-inference-parameters-1.0.0`.

Predicted and suspected observations are preserved in the audit but receive zero probability-update reliability. Farmer-reported, field-confirmed, and expert-confirmed observations receive increasing reliability.

## Spatial pressure

Nearby confirmed cases use an exponential distance-decay kernel. The distance scale is a development parameter and must be calibrated with georeferenced surveillance records.

## Loss separation

`conditional_loss` is the estimated production loss if an outbreak occurs. `expected_loss` is exactly:

```text
outbreak_probability × conditional_loss
```

Expected losses across pests overlap and must not be interpreted as independent additive realized losses.

## Diagnosis boundary

The result is an inspection-priority and outbreak-plausibility estimate. It is not laboratory identification or an official PCA diagnosis.
