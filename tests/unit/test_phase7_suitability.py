from __future__ import annotations

from app.intercropping.suitability import estimate_canopy_light, range_score
from app.intercropping import repository
from tests.phase7_factory import cell_context, prepare_phase7_production


def test_canopy_light_uses_exact_pca_row_at_reference_age():
    prepare_phase7_production()
    rows = repository.load_canopy_parameters()
    estimate = estimate_canopy_light(
        cell=cell_context(palm_age_years=40, spacing_x_m=8, spacing_y_m=8, canopy_design="square"),
        canopy_rows=rows,
        solar_radiation_mj_m2_day=18.0,
    )
    assert abs(estimate.transmitted_light_fraction - 0.37) < 1e-9
    assert len(estimate.source_parameter_ids) == 2
    assert estimate.understory_solar_radiation_mj_m2_day == 18.0 * 0.37


def test_canopy_light_interpolates_between_20_and_40_year_rows():
    prepare_phase7_production()
    estimate = estimate_canopy_light(
        cell=cell_context(palm_age_years=30, spacing_x_m=8, spacing_y_m=8, canopy_design="square"),
        canopy_rows=repository.load_canopy_parameters(),
        solar_radiation_mj_m2_day=None,
    )
    assert abs(estimate.transmitted_light_fraction - 0.285) < 1e-9
    assert estimate.age_adjusted is True


def test_range_score_has_plateau_and_decay():
    assert range_score(0.30, 0.24, 0.36) == 1.0
    assert 0 < range_score(0.20, 0.24, 0.36) < 1
    assert range_score(0.01, 0.24, 0.36) == 0
