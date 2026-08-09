from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from app.schemas.analysis import PestRiskRequest


@dataclass(frozen=True)
class EvidenceResult:
    name: str
    observed: bool
    likelihood_ratio: float


def bayes_update(prior: float, likelihood_if_event: float, likelihood_if_not_event: float) -> float:
    if not 0 < prior < 1:
        raise ValueError("prior must be between 0 and 1")
    if not 0 <= likelihood_if_event <= 1 or not 0 <= likelihood_if_not_event <= 1:
        raise ValueError("likelihoods must be between 0 and 1")
    denominator = likelihood_if_event * prior + likelihood_if_not_event * (1 - prior)
    if denominator <= 0:
        raise ValueError("evidence has zero total probability")
    return likelihood_if_event * prior / denominator


def prior_odds(probability: float) -> float:
    if not 0 < probability < 1:
        raise ValueError("probability must be between 0 and 1")
    return probability / (1 - probability)


def odds_to_probability(odds: float) -> float:
    if odds < 0:
        raise ValueError("odds cannot be negative")
    return odds / (1 + odds)


def combine_likelihood_ratios(prior: float, ratios: Iterable[float]) -> float:
    odds = prior_odds(prior)
    for ratio in ratios:
        if ratio <= 0 or not math.isfinite(ratio):
            raise ValueError("likelihood ratios must be finite and positive")
        odds *= ratio
    return odds_to_probability(odds)


def beta_posterior(alpha: float, beta: float, successes: int, failures: int) -> dict[str, float]:
    if alpha <= 0 or beta <= 0 or successes < 0 or failures < 0:
        raise ValueError("invalid Beta prior or observation count")
    a = alpha + successes
    b = beta + failures
    return {"alpha": a, "beta": b, "mean": a / (a + b), "variance": a * b / ((a + b) ** 2 * (a + b + 1))}


EVIDENCE_LR = {
    "yellowing": 1.7,
    "crown_decline": 2.1,
    "frond_cuts": 2.3,
    "visible_scale_insects": 4.2,
    "rhinoceros_beetle_damage": 4.6,
    "premature_nut_fall": 1.9,
    "nearby_reports": 2.5,
}


def evaluate_pest_risk(request: PestRiskRequest, ml_probability: float | None = None) -> dict:
    evidence: list[EvidenceResult] = []
    ratios: list[float] = []
    symptom_data = request.symptoms.model_dump()
    for name, lr in EVIDENCE_LR.items():
        observed = bool(symptom_data.get(name))
        applied = lr if observed else 1.0
        evidence.append(EvidenceResult(name, observed, applied))
        ratios.append(applied)

    if request.symptoms.severity > 0:
        severity_lr = 1 + 0.55 * request.symptoms.severity
        ratios.append(severity_lr)
        evidence.append(EvidenceResult("severity", True, severity_lr))

    humidity_lr = 1.0 + max(0.0, request.humidity_percent - 75) / 100
    rain_lr = 1.0 + min(0.45, max(0.0, request.rainfall_mm_month - 180) / 800)
    age_lr = 1.0 + max(0.0, request.average_tree_age - 45) / 180
    ratios.extend([humidity_lr, rain_lr, age_lr])
    evidence.extend([
        EvidenceResult("high_humidity", request.humidity_percent > 75, humidity_lr),
        EvidenceResult("wet_conditions", request.rainfall_mm_month > 180, rain_lr),
        EvidenceResult("aging_palms", request.average_tree_age > 45, age_lr),
    ])

    posterior = combine_likelihood_ratios(request.prior_probability, ratios)
    if ml_probability is not None:
        ml_probability = min(0.999, max(0.001, ml_probability))
        # Pool rule-based posterior and ML probability in log-odds space.
        pooled_odds = math.sqrt(prior_odds(posterior) * prior_odds(ml_probability))
        posterior = odds_to_probability(pooled_odds)

    beta = beta_posterior(3, 17, request.confirmed_positive_reports, request.confirmed_negative_reports)
    historical_posterior = beta["mean"]
    final = 0.75 * posterior + 0.25 * historical_posterior
    risk_class = "Low" if final < 0.25 else "Moderate" if final < 0.5 else "High" if final < 0.75 else "Critical"

    return {
        "prior_probability": request.prior_probability,
        "posterior_probability": round(final, 6),
        "risk_class": risk_class,
        "evidence": [item.__dict__ for item in evidence],
        "beta_posterior": beta,
        "ml_probability": ml_probability,
        "assumptions": [
            "Likelihood ratios are reference-based development assumptions pending expert calibration.",
            "Evidence items are combined using a conditional-independence approximation.",
            "The ML probability is trained on synthetic reference-based data when available.",
        ],
    }
