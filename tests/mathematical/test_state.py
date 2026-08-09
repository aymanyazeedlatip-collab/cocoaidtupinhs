import numpy as np
from app.math.state import transition_matrix, stochastic_transition, validate_transition_matrix


def test_transition_rows_sum_to_one():
    for intervention in ["no_intervention", "monitoring", "pest_management", "soil_rehabilitation", "partial_replanting", "combined_rehabilitation"]:
        matrix = transition_matrix(intervention, 0.4, 0.35, "drought")
        validate_transition_matrix(matrix)
        assert np.allclose(matrix.sum(axis=1), 1)
        assert np.all((matrix >= 0) & (matrix <= 1))


def test_state_conservation_and_nonnegative_counts():
    counts = np.array([70,360,110,45,25,20,20])
    rng = np.random.default_rng(42)
    output = stochastic_transition(counts, transition_matrix("combined_rehabilitation", 0.3, 0.2, "normal"), rng, 0.05)
    assert output.sum() == counts.sum()
    assert np.all(output >= 0)


def test_replanting_maturity_is_delayed():
    matrix = transition_matrix("partial_replanting", 0.1, 0.1, "normal")
    assert matrix[0, 0] > matrix[0, 1]
    assert matrix[0, 1] < 0.30
