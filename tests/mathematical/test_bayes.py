import math
from app.math.bayes import bayes_update, combine_likelihood_ratios, beta_posterior, odds_to_probability, prior_odds


def test_hand_calculated_bayes_example():
    posterior = bayes_update(0.20, 0.75, 0.25)
    assert math.isclose(posterior, 0.4285714286, rel_tol=1e-8)


def test_likelihood_ratio_combination():
    result = combine_likelihood_ratios(0.20, [3.0, 1.8, 2.5])
    assert math.isclose(result, 3.375 / 4.375, rel_tol=1e-8)


def test_beta_posterior_update():
    posterior = beta_posterior(16, 4, 18, 7)
    assert posterior["alpha"] == 34
    assert posterior["beta"] == 11
    assert math.isclose(posterior["mean"], 34 / 45)


def test_odds_roundtrip():
    for p in [0.01, 0.2, 0.5, 0.9]:
        assert math.isclose(odds_to_probability(prior_odds(p)), p)
