from __future__ import annotations

import numpy as np

STATES = ["young", "productive", "aging", "stressed", "infested", "recovering", "dead"]

BASE_MATRIX = np.array([
    [0.78, 0.16, 0.00, 0.03, 0.01, 0.01, 0.01],
    [0.00, 0.90, 0.035, 0.035, 0.015, 0.010, 0.005],
    [0.00, 0.00, 0.85, 0.06, 0.025, 0.035, 0.030],
    [0.00, 0.16, 0.04, 0.62, 0.07, 0.08, 0.03],
    [0.00, 0.05, 0.02, 0.10, 0.62, 0.16, 0.05],
    [0.02, 0.24, 0.02, 0.05, 0.03, 0.62, 0.02],
    [0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 1.00],
], dtype=float)

# Replant is an annual planting-position fraction, not a one-time percentage.
# Values are deliberately conservative to avoid replacing most of a farm in only a few years.
SCENARIO_EFFECTS = {
    "no_intervention": {"pest": 0.0, "soil": 0.0, "replant": 0.0, "recovery": 0.0},
    "monitoring": {"pest": 0.08, "soil": 0.0, "replant": 0.0, "recovery": 0.02},
    "pest_management": {"pest": 0.30, "soil": 0.0, "replant": 0.0, "recovery": 0.10},
    "soil_rehabilitation": {"pest": 0.05, "soil": 0.20, "replant": 0.0, "recovery": 0.08},
    "partial_replanting": {"pest": 0.05, "soil": 0.03, "replant": 0.040, "recovery": 0.04},
    "combined_rehabilitation": {"pest": 0.27, "soil": 0.18, "replant": 0.055, "recovery": 0.14},
}


def validate_transition_matrix(matrix: np.ndarray, atol: float = 1e-8) -> None:
    matrix = np.asarray(matrix, dtype=float)
    if matrix.shape != (7, 7):
        raise ValueError("transition matrix must be 7x7")
    if np.any(matrix < -atol) or np.any(matrix > 1 + atol):
        raise ValueError("transition probabilities must stay between 0 and 1")
    if not np.allclose(matrix.sum(axis=1), 1.0, atol=atol):
        raise ValueError("each transition row must sum to 1")


def _adjust_one(intervention: str, climate_stress: float, pest_risk: float, event: str) -> np.ndarray:
    if intervention not in SCENARIO_EFFECTS:
        raise ValueError(f"unknown intervention {intervention}")
    p = BASE_MATRIX.copy()
    eff = SCENARIO_EFFECTS[intervention]
    climate_stress = float(np.clip(climate_stress, 0, 1))
    pest_risk = float(np.clip(pest_risk, 0, 1))

    stress_add = 0.08 * climate_stress
    pest_add = 0.08 * pest_risk * (1 - eff["pest"])
    for row in (1, 2):
        take = min(max(0.0, p[row, row] - 0.4), stress_add + pest_add)
        p[row, row] -= take
        p[row, 3] += take * 0.58
        p[row, 4] += take * 0.42

    recovered = min(max(0.0, p[4, 4] - 0.25), 0.18 * eff["pest"] + 0.08 * eff["recovery"])
    p[4, 4] -= recovered
    p[4, 5] += recovered
    stressed_recovery = min(max(0.0, p[3, 3] - 0.25), 0.12 * eff["soil"] + 0.06 * eff["recovery"])
    p[3, 3] -= stressed_recovery
    p[3, 5] += stressed_recovery

    if event == "typhoon":
        for row in (0, 1, 2, 3, 4, 5):
            mortality = min(max(0.0, p[row, row] - 0.10), 0.03 + 0.06 * climate_stress)
            p[row, row] -= mortality
            p[row, 6] += mortality
    elif event == "drought":
        for row in (0, 1, 2, 5):
            shift = min(max(0.0, p[row, row] - 0.10), 0.02 + 0.045 * climate_stress)
            p[row, row] -= shift
            p[row, 3] += shift
    elif event == "extreme_rain":
        for row in (1, 2, 3):
            shift = min(max(0.0, p[row, row] - 0.10), 0.015 + 0.03 * pest_risk)
            p[row, row] -= shift
            p[row, 4] += shift
    elif event == "heat_stress":
        for row in (0, 1, 2):
            shift = min(max(0.0, p[row, row] - 0.10), 0.02 + 0.035 * climate_stress)
            p[row, row] -= shift
            p[row, 3] += shift

    p = np.clip(p, 0, None)
    p /= p.sum(axis=1, keepdims=True)
    validate_transition_matrix(p)
    return p


def transition_matrix(intervention: str, climate_stress: float, pest_risk: float, event: str) -> np.ndarray:
    return _adjust_one(intervention, climate_stress, pest_risk, event)


def transition_matrices(intervention: str, climate_stress: np.ndarray, pest_risk: np.ndarray, events: np.ndarray) -> np.ndarray:
    if intervention not in SCENARIO_EFFECTS:
        raise ValueError(f"unknown intervention {intervention}")
    climate_stress = np.clip(np.asarray(climate_stress, dtype=float), 0, 1)
    pest_risk = np.clip(np.asarray(pest_risk, dtype=float), 0, 1)
    events = np.asarray(events)
    if climate_stress.shape != pest_risk.shape or climate_stress.shape != events.shape:
        raise ValueError("batch transition inputs must have matching shapes")
    runs = len(climate_stress)
    p = np.broadcast_to(BASE_MATRIX, (runs, 7, 7)).copy()
    eff = SCENARIO_EFFECTS[intervention]

    take = np.minimum(BASE_MATRIX[1, 1] - 0.4, 0.08 * climate_stress + 0.08 * pest_risk * (1 - eff["pest"]))
    for row in (1, 2):
        p[:, row, row] -= take
        p[:, row, 3] += take * 0.58
        p[:, row, 4] += take * 0.42

    recovered = min(BASE_MATRIX[4, 4] - 0.25, 0.18 * eff["pest"] + 0.08 * eff["recovery"])
    p[:, 4, 4] -= recovered
    p[:, 4, 5] += recovered
    stressed_recovery = min(BASE_MATRIX[3, 3] - 0.25, 0.12 * eff["soil"] + 0.06 * eff["recovery"])
    p[:, 3, 3] -= stressed_recovery
    p[:, 3, 5] += stressed_recovery

    typhoon = events == "typhoon"
    drought = events == "drought"
    extreme_rain = events == "extreme_rain"
    heat = events == "heat_stress"
    for row in (0, 1, 2, 3, 4, 5):
        mortality = np.minimum(p[:, row, row] - 0.10, 0.03 + 0.06 * climate_stress)
        mortality = np.where(typhoon, np.maximum(0, mortality), 0)
        p[:, row, row] -= mortality
        p[:, row, 6] += mortality
    for row in (0, 1, 2, 5):
        shift = np.minimum(p[:, row, row] - 0.10, 0.02 + 0.045 * climate_stress)
        shift = np.where(drought, np.maximum(0, shift), 0)
        p[:, row, row] -= shift
        p[:, row, 3] += shift
    for row in (1, 2, 3):
        shift = np.minimum(p[:, row, row] - 0.10, 0.015 + 0.03 * pest_risk)
        shift = np.where(extreme_rain, np.maximum(0, shift), 0)
        p[:, row, row] -= shift
        p[:, row, 4] += shift
    for row in (0, 1, 2):
        shift = np.minimum(p[:, row, row] - 0.10, 0.02 + 0.035 * climate_stress)
        shift = np.where(heat, np.maximum(0, shift), 0)
        p[:, row, row] -= shift
        p[:, row, 3] += shift

    p = np.clip(p, 0, None)
    p /= p.sum(axis=2, keepdims=True)
    return p


def stochastic_transition_batch(
    counts: np.ndarray,
    matrices: np.ndarray,
    rng: np.random.Generator,
    replant_fraction: float | np.ndarray = 0.0,
) -> np.ndarray:
    counts = np.asarray(counts, dtype=int)
    matrices = np.asarray(matrices, dtype=float)
    if counts.ndim != 2 or counts.shape[1] != 7 or np.any(counts < 0):
        raise ValueError("counts must have shape (runs, 7) with nonnegative integers")
    if matrices.shape != (counts.shape[0], 7, 7):
        raise ValueError("matrices must have shape (runs, 7, 7)")
    if np.any(matrices < -1e-9) or not np.allclose(matrices.sum(axis=2), 1.0, atol=1e-8):
        raise ValueError("invalid batch transition probabilities")

    runs = counts.shape[0]
    output = np.zeros_like(counts)
    for source in range(7):
        remaining_n = counts[:, source].copy()
        remaining_p = np.ones(runs, dtype=float)
        for dest in range(6):
            conditional_p = np.divide(
                matrices[:, source, dest], remaining_p,
                out=np.zeros(runs, dtype=float), where=remaining_p > 1e-12,
            )
            conditional_p = np.clip(conditional_p, 0, 1)
            draw = rng.binomial(remaining_n, conditional_p)
            output[:, dest] += draw
            remaining_n -= draw
            remaining_p -= matrices[:, source, dest]
        output[:, 6] += remaining_n

    fractions = np.broadcast_to(np.asarray(replant_fraction, dtype=float), (runs,))
    fractions = np.clip(fractions, 0, 0.10)
    targets = np.rint(output.sum(axis=1) * fractions).astype(int)
    moved = np.zeros(runs, dtype=int)
    # Fill vacant planting positions first. Only a limited fraction of aging or
    # infested palms may be replaced in a single year.
    for source, cap_fraction in ((6, 1.0), (2, 0.20), (4, 0.20)):
        cap = output[:, source] if source == 6 else np.rint(output[:, source] * cap_fraction).astype(int)
        take = np.minimum(cap, np.maximum(0, targets - moved))
        output[:, source] -= take
        output[:, 0] += take
        moved += take

    if not np.array_equal(output.sum(axis=1), counts.sum(axis=1)):
        raise RuntimeError("state transition did not conserve total planting positions")
    return output


def stochastic_transition(counts: np.ndarray, matrix: np.ndarray, rng: np.random.Generator, replant_fraction: float = 0.0) -> np.ndarray:
    counts = np.asarray(counts, dtype=int)
    if counts.shape != (7,) or np.any(counts < 0):
        raise ValueError("counts must be seven nonnegative integers")
    validate_transition_matrix(matrix)
    return stochastic_transition_batch(counts[None, :], matrix[None, :, :], rng, replant_fraction)[0]
