# Mathematical Model

The authoritative source document is included in `docs/reference/COCOGUARD_Mathematical_Framework_Source.docx`. The application name is standardized to COCO-AID, while the mathematical design follows that framework.

## Central outputs

For each intervention strategy, COCO-AID estimates:

1. A distribution of future annual production
2. Rehabilitation and severe-loss probabilities
3. Risk-adjusted expected utility and the preferred strategy

## Bayesian pest update

For hypothesis `H` and evidence `E`:

```text
P(H|E) = P(E|H)P(H) / [P(E|H)P(H) + P(E|not H)P(not H)]
```

Multiple evidence items are combined through prior odds multiplied by evidence likelihood ratios. The current implementation explicitly reports the prior, evidence multipliers, posterior, and conditional-independence assumption.

A Beta prior supports updating event frequencies:

```text
p ~ Beta(alpha, beta)
p | data ~ Beta(alpha + positives, beta + negatives)
```

## Farm state

The seven tree states are:

```text
Young, Productive, Aging, Stressed, Infested, Recovering, Dead
```

A scenario-dependent transition matrix maps current state counts to the next year. Rows sum to one; multinomial sampling creates stochastic transitions while preserving total planting positions.

## Production

Annual production depends on productive-equivalent trees, health state, suitability, climate stress, pest pressure, management, and sampled weather-event severity. Productive capacity and health are evaluated against explicit provisional reference shares rather than normalized against each farm's own starting damage. This prevents two farms with the same entered production but substantially different infestation and vacancy levels from being treated as biologically equivalent. A bounded ML correction augments but does not replace the transparent equation.

The current development reference assumptions are documented in code and output limitations. They require field calibration.

## Climate-conditioned hazards

Each future year samples an event from:

```text
Normal, Drought, Extreme Rain, Heat Stress, Typhoon
```

Event probabilities depend on the selected SSP, future period, latitude-dependent exposure, and compact development climate parameters. Generated events are plausible simulated futures, not exact forecasts.

## Monte Carlo outputs

Across `M` paths, the engine calculates mean, median, 5th, 25th, 75th, and 95th percentiles, state means, rehabilitation probability, severe-loss probability, cumulative probability of at least one major weather-loss year, annualized weather-loss rate, and recovery timing.

A path is considered rehabilitated at the horizon when production reaches the declared threshold (85% by default) and productive plus recovering palms meet the health-share condition. Recovery timing requires three consecutive qualifying years and is reported only for paths that remain recovered at the final year.

## Decision optimization

The scenario score is a normalized discounted production benefit minus intervention burden and a severe-loss penalty:

```text
U(a) = E[discounted production | a] - C(a) - lambda P(severe loss | a)
```

The application ranks six interventions by this declared utility rule. Burden values are research assumptions, not peso-denominated costs.

## Daily visualization layer

The validated biological state transition remains annual. For visualization between annual states, each state count is linearly interpolated within the year and disclosed as an estimate. A transient weather indicator modifies only the displayed daily condition score and does not silently change the annual posterior state.

For one sampled annual production value \(Y_y\), nonnegative daily weights \(w_d\) are derived from seasonality, temperature stress, moisture stress, and event severity, then normalized:

\[
\sum_{d \in y} w_d = 1,
\qquad
\widetilde{Y}_d = w_d Y_y.
\]

\(\widetilde{Y}_d\) is called a **daily production equivalent**. It is not asserted to be the farm's exact harvest on day \(d\).

Dates within the live numerical model horizon may replace the generated weather variables with provider forecast values. This replacement changes the daily visualization and weighting for those dates but does not mislabel the long-term stochastic sequence as provider output.
