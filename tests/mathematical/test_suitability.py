from app.math.suitability import trapezoid_membership, suitability_index
from app.schemas.analysis import SuitabilityRequest


def test_membership_bounds():
    assert trapezoid_membership(5, 0, 4, 6, 10) == 1
    assert trapezoid_membership(0, 0, 4, 6, 10) == 0
    assert 0 < trapezoid_membership(2, 0, 4, 6, 10) < 1


def test_suitability_is_bounded():
    result = suitability_index(SuitabilityRequest())
    assert 0 <= result["score"] <= 1
    assert result["class"] in {"Unsuitable", "Marginal", "Moderately Suitable", "Suitable", "Highly Suitable"}
