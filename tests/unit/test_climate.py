from app.climate.projections import climate_projection, generate_annual_trajectory, year_climate_parameters
from app.schemas.analysis import ClimateProjectionRequest, ClimateTrajectoryRequest


def test_climate_projection_has_12_months():
    result = climate_projection(ClimateProjectionRequest())
    assert len(result["monthly"]) == 12
    assert result["data_source_type"] == "synthetic_reference_based"


def test_climate_scenario_changes_temperature_anomaly():
    low = year_climate_parameters(2050, "ssp126")
    high = year_climate_parameters(2050, "ssp585")
    assert high["temperature_anomaly_c"] > low["temperature_anomaly_c"]


def test_trajectory_seed_reproducibility():
    req = ClimateTrajectoryRequest(start_year=2026,end_year=2032,seed=77)
    assert generate_annual_trajectory(req) == generate_annual_trajectory(req)
