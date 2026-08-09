# Variety Adjustments and Product Conversions

## Named-variety adjustment

When a named PCA variety has `nuts_per_hectare`, COCOAID compares it with the median for its own class: Tall, Dwarf, or Hybrid. The raw factor is capped to `0.70–1.30` until field calibration is available.

The forecast stores:

- resolved variety ID and class;
- adjustment factor;
- explicit adjustment basis;
- PCA parameter-set version;
- source limitations.

No named variety or missing yield parameter results in a factor of `1.0`, not an invented value.

## Product conversions

When `fruit_weight_g` exists, annual whole-fruit mass is converted into estimated nut count. A caller-supplied young-nut share separates mature and young counts. Mature-fruit PCA component values then estimate:

- copra;
- husk;
- shell;
- meat;
- coconut water.

Components use mature-nut count because the encoded PCA component references describe mature fruit. VCO volume remains deferred because the canonical unit registry does not yet contain litres.

These are reference-based conversions, not separate ML predictions.
