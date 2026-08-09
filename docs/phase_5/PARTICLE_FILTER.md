# Particle-Filter Method

## Development priors

Phase 5 uses transparent development priors for:

- weather sensitivity;
- pest sensitivity;
- annual mortality rate;
- rehabilitation success;
- soil-recovery rate;
- pest-loss fraction;
- production multiplier;
- rainfall-bias factor.

The parameter set is versioned as `bayesian-farm-state-parameters-1.0.0`. These priors are not claimed to be PCA-calibrated or field-validated.

## Evidence update

For admissible evidence, each particle receives a reliability-weighted Gaussian observation likelihood. Effective sample size is measured after each update. Systematic resampling occurs when particle degeneracy falls below the configured internal threshold. Predicted and suspected values receive zero evidence weight.

## State propagation

The simulator propagates states monthly. Weather stress, pest pressure, soil condition, and selected intervention alter transition probabilities. Each transition matrix is row-normalized and total planting positions are conserved.

## Production propagation

The Phase 4 variety-adjusted production value is the baseline. Phase 5 applies relative changes in productive palm-state score, soil fertility, soil water, pest loss, and the sampled production multiplier. Absolute initial soil and water indices are not multiplied into the baseline a second time because they were already represented in the Phase 4 feature set.

## Reproducibility

Identical input, parameter version, particle count, and random seed produce identical posterior summaries. A sequential run begins from the prior posterior state and its moment-matched posterior parameter distributions.
