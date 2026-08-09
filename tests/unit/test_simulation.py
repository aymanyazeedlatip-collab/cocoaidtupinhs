from app.schemas.analysis import SimulationRequest, ScenarioComparisonRequest
from app.schemas.farm import FarmCreate
from app.simulation.engine import run_simulation
from app.simulation.compare import compare_scenarios


def test_simulation_reproducibility_and_percentiles():
    req = SimulationRequest(runs=100,end_year=2032,seed=22)
    a=run_simulation(req); b=run_simulation(req)
    assert a["summary"] == b["summary"]
    for row in a["yearly"]:
        assert row["p05"] <= row["median"] <= row["p95"]


def test_weather_events_affect_productivity():
    result=run_simulation(SimulationRequest(runs=100,end_year=2035,seed=44,intervention="no_intervention"))
    assert len(set(round(x["production_tons"],3) for x in result["sample_trajectory"])) > 1
    assert result["summary"]["major_weather_loss_probability"] >= 0


def test_pest_pressure_reduces_formula_outcomes_statistically():
    healthy=FarmCreate()
    unhealthy=healthy.model_copy(deep=True)
    unhealthy.trees.infested=120
    unhealthy.trees.productive-=95
    unhealthy.trees.stressed+=0
    # Keep total conserved by moving productive trees into infestation.
    a=run_simulation(SimulationRequest(farm=healthy,runs=100,end_year=2033,seed=4))
    b=run_simulation(SimulationRequest(farm=unhealthy,runs=100,end_year=2033,seed=4))
    assert b["summary"]["final_mean_tons"] < a["summary"]["final_mean_tons"]


def test_scenario_comparison_has_six_strategies_and_utility():
    result=compare_scenarios(ScenarioComparisonRequest(runs=100,end_year=2030,seed=5))
    assert len(result["ranking"]) == 6
    assert result["ranking"][0]["expected_utility"] >= result["ranking"][-1]["expected_utility"]
