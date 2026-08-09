from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Query
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.errors import CocoAidError
from app.data_foundation import repository as data_repository
from app.domain.contract_registry import contract_registry
from app.domain.production import ProductionActualInput, ProductionEngineRequest
from app.domain.bayesian import BayesianEvidenceObservation, BayesianSimulationRequest
from app.domain.pest import PestAssessmentRequest, PestObservation
from app.domain.intercropping import IntercropAssessmentRequest
from app.domain.rehabilitation import RehabilitationPlanRequest
from app.domain.decision_support import DecisionSupportRequest
from app.domain.coco_pilot import CocoPilotRequest, FormalReportRequest
from app.domain.units import CANONICAL_VARIABLE_UNITS, UNIT_CATALOG
from app.engines.registry import engine_registry
from app.engines.production import production_engine
from app.engines.bayesian import bayesian_engine
from app.engines.pest_inference import pest_inference_engine, PEST_TAXONOMY_NOTICE
from app.engines.intercropping import intercropping_engine, INTERCROP_DATA_NOTICE
from app.engines.rehabilitation import rehabilitation_engine, REHABILITATION_DATA_NOTICE
from app.engines.decision_support import decision_support_engine, DECISION_SUPPORT_DATA_NOTICE
from app.models.registry import model_metadata, model_runtime_status
from app.parameters.registry import parameter_registry
from app.production import repository as production_repository
from app.bayesian import repository as bayesian_repository
from app.pest import repository as pest_repository
from app.pest.parameters import PEST_PARAMETER_VERSION, SUPPORTED_PEST_IDS
from app.intercropping import repository as intercropping_repository
from app.rehabilitation import repository as rehabilitation_repository
from app.decision_support import repository as decision_support_repository
from app.coco_pilot import repository as coco_pilot_repository
from app.coco_pilot.service import (
    COCO_PILOT_ENGINE_VERSION, COCO_PILOT_PARAMETER_VERSION, COCO_PILOT_PROMPT_VERSION,
    coco_pilot_service,
)
from app.coco_pilot.reports import (
    FORMAL_REPORT_DATA_NOTICE, FORMAL_REPORT_GENERATOR_VERSION, generate_formal_report,
)
from app.services.assistant import assistant_status
from app.intercropping.parameters import (
    CANOPY_LIGHT_ADAPTER_VERSION, INTERCROP_PARAMETER_VERSION,
    INTERCROP_REQUIREMENT_PROFILE_VERSION,
)
from app.production.feature_adapter import LEGACY_PRODUCTION_FEATURE_ORDER, PRODUCTION_FEATURE_ADAPTER_VERSION
from app.rehabilitation.parameters import (
    REHABILITATION_PARAMETER_VERSION, REHABILITATION_COST_CATALOG_VERSION,
)
from app.decision_support.parameters import (
    DECISION_SUPPORT_PARAMETER_VERSION, DEPENDENCY_GRAPH_VERSION, DEPENDENCY_GRAPH,
)
from app.storage.migrations import MigrationManager
from app.schemas.weather_assimilation import WeatherAssimilationRequest
from app.schemas.farm import FarmCreate
from app.weather.assimilation.service import assimilate_weather
from app.weather.assimilation import repository as weather_repository
from app.interface.status import interface_status
from app.workflows.auto_phase_runner import bootstrap_from_farm, kick as kick_auto_phase_workflow, workflow_status as auto_phase_workflow_status

router = APIRouter(prefix=settings.v2_api_prefix, tags=["COCOAID v3 Contracts"])


@router.get("/health")
def health_v2() -> dict[str, Any]:
    return {
        "status": "healthy",
        "product": settings.product_name,
        "contract_api_version": settings.contract_api_version,
        "legacy_api_version": settings.api_version,
        "environment": settings.environment,
        "timestamp": datetime.now(UTC).isoformat(),
        "model_runtime": model_runtime_status(),
        "database_migrations": [asdict(item) for item in MigrationManager(settings.database_path).status()],
    }


@router.get("/interface/status")
def phase11_interface_status() -> dict[str, Any]:
    return interface_status()


@router.get("/configuration")
def public_configuration() -> dict[str, Any]:
    return settings.public_snapshot()


@router.get("/contracts")
def list_contracts() -> dict[str, Any]:
    return {
        "contract_api_version": settings.contract_api_version,
        "contracts": [entry.model_dump(mode="json") for entry in contract_registry.catalog()],
    }


@router.get("/contracts/{contract_name}")
def get_contract(contract_name: str) -> dict[str, Any]:
    entry = contract_registry.entry(contract_name)
    return {
        "contract": entry.model_dump(mode="json"),
        "json_schema": contract_registry.schema(contract_name),
    }


@router.post("/contracts/{contract_name}/validate")
def validate_contract(contract_name: str, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    validated = contract_registry.validate(contract_name, payload)
    return {
        "valid": True,
        "contract_name": contract_name,
        "normalized": validated.model_dump(mode="json"),
    }


@router.get("/engines")
def list_engines() -> dict[str, Any]:
    return {
        "engines": [item.model_dump(mode="json") for item in engine_registry.descriptors()],
        "note": "Contract-only engines are not executable until their development phase is completed.",
    }


@router.get("/engines/{engine_id}")
def get_engine(engine_id: str) -> dict[str, Any]:
    return engine_registry.descriptor(engine_id).model_dump(mode="json")


@router.get("/models")
def list_models_v2() -> dict[str, Any]:
    return {"runtime": model_runtime_status(), "models": model_metadata()}


@router.get("/parameters")
def list_parameters() -> dict[str, Any]:
    return {"parameter_sets": [item.model_dump(mode="json") for item in parameter_registry.descriptors()]}


@router.get("/units")
def list_units() -> dict[str, Any]:
    return {
        "units": [UNIT_CATALOG[key].model_dump(mode="json") for key in sorted(UNIT_CATALOG, key=lambda unit: unit.value)],
        "canonical_variable_units": {key: value.value for key, value in sorted(CANONICAL_VARIABLE_UNITS.items())},
    }


@router.get("/database/migrations")
def migration_status() -> dict[str, Any]:
    return {"migrations": [asdict(item) for item in MigrationManager(settings.database_path).status()]}


@router.get("/data-foundation/summary")
def data_foundation_summary() -> dict[str, Any]:
    return {
        "catalog_version": "phase4-pca-and-economic-reference-1",
        "counts": data_repository.summary(),
        "privacy": {
            "farmer_names_exposed": False,
            "restricted_source_documents_exposed": False,
            "note": "Farmer identities are isolated from analytical registry records.",
        },
    }


@router.get("/data-foundation/source-documents")
def source_documents() -> dict[str, Any]:
    return {"documents": data_repository.list_source_documents(include_restricted=False)}


@router.get("/data-foundation/varieties")
def varieties(variety_class: str | None = Query(default=None, pattern="^(tall|dwarf|hybrid)$")) -> dict[str, Any]:
    return {"varieties": data_repository.list_varieties(variety_class)}


@router.get("/data-foundation/pests")
def pests() -> dict[str, Any]:
    return {"pests": data_repository.list_pests()}


@router.get("/data-foundation/intercrops")
def intercrops() -> dict[str, Any]:
    return {
        "model_status": "reference_catalog_only",
        "warning": "These records are inputs for a future transparent scoring engine, not supervised ML predictions.",
        "candidates": data_repository.list_intercrops(),
    }


@router.get("/data-foundation/canopy-light")
def canopy_light(age_years: int | None = Query(default=None, ge=20, le=40)) -> dict[str, Any]:
    if age_years not in (None, 20, 40):
        from app.core.errors import CocoAidError
        raise CocoAidError("Canopy light reference supports only 20- and 40-year-old stands", status_code=422)
    return {"parameters": data_repository.list_canopy_light_parameters(age_years=age_years)}


@router.get("/data-foundation/fertilization-scenarios")
def fertilization_scenarios() -> dict[str, Any]:
    return {
        "scenarios": data_repository.list_fertilization_scenarios(),
        "warning": "Scenarios are optional references and require local agronomic validation.",
    }


@router.get("/data-foundation/farmer-import-runs")
def farmer_import_runs() -> dict[str, Any]:
    return {"runs": data_repository.list_farmer_import_runs()}


@router.get("/data-foundation/farmer-registry-summary")
def farmer_registry_summary() -> dict[str, Any]:
    return data_repository.farmer_registry_summary()


@router.get("/weather/status")
def weather_assimilation_status() -> dict[str, Any]:
    return {
        "engine_id": "v3.weather_assimilation",
        "engine_version": "1.0.1",
        "provider_hotfix": "weather-provider-resilience-1.0.1",
        "status": "available",
        "live_forecast_limit_days": settings.max_live_forecast_days,
        "feature_adapter_version": "weather-features-1.0.0",
        "storage": weather_repository.summary(),
        "provider_resilience": {
            "connect_timeout_seconds": settings.weather_connect_timeout_seconds,
            "read_timeout_seconds": settings.weather_read_timeout_seconds,
            "attempts_per_network_mode": settings.weather_request_attempts,
            "direct_connection_fallback": settings.weather_direct_connection_fallback,
            "system_trust_store": settings.weather_use_system_trust_store,
        },
        "boundaries": {
            "live_weather": "Current conditions plus forecast Days 1-16 only.",
            "long_term": "Longer horizons are climate-conditioned simulations, not live forecasts.",
            "model_retraining": "Weather refreshes predictions; it does not retrain the retained ML model.",
        },
    }


@router.post("/weather/assimilate")
async def weather_assimilate(request: WeatherAssimilationRequest) -> dict[str, Any]:
    return await assimilate_weather(request)


@router.get("/weather/runs")
def weather_runs(
    limit: int = Query(default=50, ge=1, le=200),
    latitude: float | None = Query(default=None, ge=-90, le=90),
    longitude: float | None = Query(default=None, ge=-180, le=180),
) -> dict[str, Any]:
    runs = weather_repository.list_runs(limit=limit, latitude=latitude, longitude=longitude)
    return {"runs": runs, "count": len(runs)}


@router.get("/weather/runs/{run_id}")
def weather_run(
    run_id: UUID,
    include_values: bool = Query(default=False),
    period_kind: str | None = Query(default=None, pattern="^(historical|current|forecast)$"),
) -> dict[str, Any]:
    run = weather_repository.get_run(run_id, include_values=include_values, period_kind=period_kind)
    if not run:
        raise CocoAidError("Weather run not found", status_code=404, details={"weather_run_id": str(run_id)})
    return run


@router.get("/weather/runs/{run_id}/features")
def weather_run_features(run_id: UUID) -> dict[str, Any]:
    feature_set = weather_repository.get_feature_set_for_run(run_id)
    if not feature_set:
        raise CocoAidError(
            "No agricultural weather feature set is stored for this run",
            status_code=404,
            details={"weather_run_id": str(run_id)},
        )
    return feature_set


@router.get("/weather/compare")
def weather_compare(base_run_id: UUID, comparison_run_id: UUID) -> dict[str, Any]:
    try:
        return weather_repository.compare_runs(base_run_id, comparison_run_id)
    except KeyError as exc:
        raise CocoAidError(str(exc).strip("'"), status_code=404) from exc
    except ValueError as exc:
        raise CocoAidError(str(exc), status_code=422) from exc


@router.get("/data-foundation/intercrop-income-assessment")
def intercrop_income_assessment() -> dict[str, Any]:
    return data_repository.intercrop_income_assessment()


@router.get("/production/status")
def production_status() -> dict[str, Any]:
    descriptor = production_engine.descriptor
    metadata = model_metadata("production").get("production", {})
    return {
        "engine": descriptor.model_dump(mode="json"),
        "feature_adapter_version": PRODUCTION_FEATURE_ADAPTER_VERSION,
        "frozen_feature_order": LEGACY_PRODUCTION_FEATURE_ORDER,
        "retained_model": metadata,
        "storage": production_repository.summary(),
        "output_layers": {
            "raw_ml_prediction": "Retained production-model output.",
            "variety_adjusted_prediction": "Bounded within-class adjustment using named PCA variety references when available.",
            "posterior_prediction": "Not run in Phase 4; reserved for the Phase 5 Bayesian engine.",
        },
    }


@router.post("/production/forecast")
def production_forecast(request: ProductionEngineRequest) -> dict[str, Any]:
    result = production_engine.execute(request)
    return result.model_dump(mode="json")


@router.get("/production/forecasts")
def production_forecasts(
    farm_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    items = production_repository.list_forecasts(farm_id=farm_id, limit=limit)
    return {"forecasts": items, "count": len(items)}


@router.get("/production/forecasts/{forecast_id}")
def production_forecast_record(forecast_id: UUID) -> dict[str, Any]:
    item = production_repository.get_forecast(forecast_id)
    if not item:
        raise CocoAidError("Production forecast not found", status_code=404, details={"forecast_id": str(forecast_id)})
    return item


@router.post("/production/actuals")
def production_actual(actual: ProductionActualInput) -> dict[str, Any]:
    try:
        actual_id = production_repository.save_actual(actual)
    except KeyError as exc:
        raise CocoAidError(str(exc).strip("'"), status_code=404) from exc
    except ValueError as exc:
        raise CocoAidError(str(exc), status_code=422) from exc
    return {"actual_id": actual_id, "stored": True}


@router.get("/production/forecasts/{forecast_id}/performance")
def production_forecast_performance(forecast_id: UUID) -> dict[str, Any]:
    item = production_repository.forecast_performance(forecast_id)
    if not item:
        raise CocoAidError("Production forecast not found", status_code=404, details={"forecast_id": str(forecast_id)})
    return item


@router.get("/bayesian/status")
def bayesian_status() -> dict[str, Any]:
    descriptor = bayesian_engine.descriptor
    return {
        "engine": descriptor.model_dump(mode="json"),
        "parameter_version": "bayesian-farm-state-parameters-1.0.0",
        "storage": bayesian_repository.summary(),
        "default_particle_count": settings.default_simulation_runs,
        "maximum_particle_count": settings.max_simulation_runs,
        "evidence_policy": {
            "predicted": "stored but not assimilated",
            "suspected": "stored but not assimilated",
            "farmer_reported": "assimilated with reduced reliability",
            "field_confirmed": "assimilated with high reliability",
            "expert_confirmed": "assimilated with full reliability",
        },
        "posterior_linkage": "Successful runs update the linked production forecast posterior layer without retraining its ML model.",
    }


@router.post("/bayesian/observations")
def bayesian_observation(observation: BayesianEvidenceObservation) -> dict[str, Any]:
    try:
        observation_id = bayesian_repository.save_observation(observation)
    except KeyError as exc:
        raise CocoAidError(str(exc).strip("'"), status_code=404) from exc
    except ValueError as exc:
        raise CocoAidError(str(exc), status_code=422) from exc
    return {
        "observation_id": str(observation_id),
        "stored": True,
        "will_update_posterior": observation.evidence_status.value not in {"predicted", "suspected"},
    }


@router.get("/bayesian/observations")
def bayesian_observations(
    farm_id: UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    items = bayesian_repository.list_observations(farm_id=farm_id, limit=limit)
    return {"observations": items, "count": len(items)}


@router.post("/bayesian/simulate")
def bayesian_simulate(request: BayesianSimulationRequest) -> dict[str, Any]:
    result = bayesian_engine.execute(request)
    return result.model_dump(mode="json")


@router.get("/bayesian/posteriors")
def bayesian_posteriors(
    farm_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    items = bayesian_repository.list_posteriors(farm_id=farm_id, limit=limit)
    return {"posteriors": items, "count": len(items)}


@router.get("/bayesian/posteriors/{posterior_id}")
def bayesian_posterior_record(posterior_id: UUID) -> dict[str, Any]:
    item = bayesian_repository.get_posterior(posterior_id)
    if not item:
        raise CocoAidError("Bayesian posterior not found", status_code=404, details={"posterior_id": str(posterior_id)})
    return item

@router.get("/pests/status")
def pest_inference_status() -> dict[str, Any]:
    return {
        "engine": pest_inference_engine.descriptor.model_dump(mode="json"),
        "parameter_version": PEST_PARAMETER_VERSION,
        "supported_pest_profile_ids": list(SUPPORTED_PEST_IDS),
        "storage": pest_repository.summary(),
        "taxonomy_notice": PEST_TAXONOMY_NOTICE,
        "evidence_policy": {
            "predicted": "stored for traceability; does not change probability",
            "suspected": "stored for traceability; does not change probability",
            "farmer_reported": "used with reduced reliability",
            "field_confirmed": "used with high reliability",
            "expert_confirmed": "used with full reliability",
        },
        "loss_policy": {
            "conditional_loss": "Estimated production loss if the outbreak occurs.",
            "expected_loss": "Outbreak probability multiplied by conditional loss.",
            "multi_pest_warning": "Pest losses overlap and are not independent additive realized losses.",
        },
    }


@router.get("/pests/profiles")
def pest_inference_profiles(
    pest_profile_id: str | None = Query(default=None),
) -> dict[str, Any]:
    requested = [pest_profile_id] if pest_profile_id else list(SUPPORTED_PEST_IDS)
    unsupported = sorted(set(requested) - set(SUPPORTED_PEST_IDS))
    if unsupported:
        raise CocoAidError(
            "Unsupported Phase 6 pest profile",
            status_code=422,
            details={"unsupported": unsupported, "supported": list(SUPPORTED_PEST_IDS)},
        )
    return {
        "profiles": pest_repository.load_reference_profiles(requested),
        "taxonomy_notice": PEST_TAXONOMY_NOTICE,
        "warning": "Qualitative PCA rules are source-backed; numerical likelihood ratios are versioned development parameters.",
    }


@router.post("/pests/observations")
def pest_observation(observation: PestObservation) -> dict[str, Any]:
    try:
        observation_id, bayesian_observation_id = pest_repository.save_observation(observation)
    except KeyError as exc:
        raise CocoAidError(str(exc).strip("'"), status_code=404) from exc
    except ValueError as exc:
        raise CocoAidError(str(exc), status_code=422) from exc
    return {
        "observation_id": str(observation_id),
        "stored": True,
        "used_for_pest_probability": observation.evidence_status.value not in {"predicted", "suspected"},
        "bayesian_observation_id": str(bayesian_observation_id) if bayesian_observation_id else None,
        "bayesian_link_created": bayesian_observation_id is not None,
        "note": "A Bayesian pest-prevalence observation is created only when prevalence_fraction is supplied.",
    }


@router.get("/pests/observations")
def pest_observations(
    farm_id: UUID | None = Query(default=None),
    pest_profile_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    if pest_profile_id and pest_profile_id not in SUPPORTED_PEST_IDS:
        raise CocoAidError(
            "Unsupported Phase 6 pest profile",
            status_code=422,
            details={"supported": list(SUPPORTED_PEST_IDS)},
        )
    items = pest_repository.list_observations(
        farm_id=farm_id, pest_profile_id=pest_profile_id, limit=limit,
    )
    return {"observations": items, "count": len(items)}


@router.post("/pests/assess")
def pest_assess(request: PestAssessmentRequest) -> dict[str, Any]:
    result = pest_inference_engine.execute(request)
    return result.model_dump(mode="json")


@router.get("/pests/assessments")
def pest_assessments(
    farm_id: UUID | None = Query(default=None),
    pest_profile_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    if pest_profile_id and pest_profile_id not in SUPPORTED_PEST_IDS:
        raise CocoAidError(
            "Unsupported Phase 6 pest profile",
            status_code=422,
            details={"supported": list(SUPPORTED_PEST_IDS)},
        )
    items = pest_repository.list_assessments(
        farm_id=farm_id, pest_profile_id=pest_profile_id, limit=limit,
    )
    return {"assessments": items, "count": len(items)}


@router.get("/pests/assessments/{assessment_id}")
def pest_assessment_record(assessment_id: UUID) -> dict[str, Any]:
    item = pest_repository.get_assessment(assessment_id)
    if not item:
        raise CocoAidError(
            "Pest assessment not found", status_code=404,
            details={"assessment_id": str(assessment_id)},
        )
    return item


@router.get("/intercropping/status")
def intercropping_status() -> dict[str, Any]:
    return {
        "engine": intercropping_engine.descriptor.model_dump(mode="json"),
        "parameter_version": INTERCROP_PARAMETER_VERSION,
        "requirement_profile_version": INTERCROP_REQUIREMENT_PROFILE_VERSION,
        "canopy_light_adapter_version": CANOPY_LIGHT_ADAPTER_VERSION,
        "storage": intercropping_repository.summary(),
        "model_type": "evidence_scoring",
        "data_notice": INTERCROP_DATA_NOTICE,
        "economic_scope": {
            "available_candidates": ["cacao", "coffee"],
            "metric": "historical gross revenue scenario",
            "not_claimed": ["net profit", "ROI", "guaranteed future income"],
        },
    }


@router.get("/intercropping/candidates")
def intercropping_candidates(
    candidate_id: str | None = Query(default=None),
) -> dict[str, Any]:
    requested = [candidate_id] if candidate_id else None
    candidates = intercropping_repository.load_candidates(requested)
    if candidate_id and not candidates:
        raise CocoAidError(
            "Intercrop candidate not found", status_code=404,
            details={"candidate_id": candidate_id},
        )
    return {
        "candidates": candidates,
        "count": len(candidates),
        "warning": "PCA supports light bands; non-light numerical requirements are versioned development assumptions.",
    }


@router.post("/intercropping/assess")
def intercropping_assess(request: IntercropAssessmentRequest) -> dict[str, Any]:
    result = intercropping_engine.execute(request)
    return result.model_dump(mode="json")


@router.get("/intercropping/assessments")
def intercropping_assessments(
    farm_id: UUID | None = Query(default=None),
    candidate_id: str | None = Query(default=None),
    cell_id: UUID | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
) -> dict[str, Any]:
    items = intercropping_repository.list_assessments(
        farm_id=farm_id, candidate_id=candidate_id, cell_id=cell_id, limit=limit,
    )
    return {"assessments": items, "count": len(items)}


@router.get("/intercropping/assessments/{assessment_id}")
def intercropping_assessment_record(assessment_id: UUID) -> dict[str, Any]:
    item = intercropping_repository.get_assessment(assessment_id)
    if not item:
        raise CocoAidError(
            "Intercrop assessment not found", status_code=404,
            details={"assessment_id": str(assessment_id)},
        )
    return item

@router.get("/rehabilitation/status")
def rehabilitation_status() -> dict[str, Any]:
    return {
        "engine": rehabilitation_engine.descriptor.model_dump(mode="json"),
        "parameter_version": REHABILITATION_PARAMETER_VERSION,
        "cost_catalog_version": REHABILITATION_COST_CATALOG_VERSION,
        "storage": rehabilitation_repository.summary(),
        "scenario_types": [
            "no_action", "pest_management", "fertilization", "replanting",
            "intercropping", "combined_rehabilitation",
        ],
        "safety_policy": {
            "predicted_hazards_are_confirmed_damage": False,
            "inferred_pest_risk_triggers": "inspection and preparation",
            "chemical_dosage_generated": False,
            "no_action_always_compared": True,
        },
        "data_notice": REHABILITATION_DATA_NOTICE,
    }


@router.post("/rehabilitation/plan")
def rehabilitation_plan(request: RehabilitationPlanRequest) -> dict[str, Any]:
    result = rehabilitation_engine.execute(request)
    return result.model_dump(mode="json")


@router.get("/rehabilitation/plans")
def rehabilitation_plans(
    farm_id: UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    items = rehabilitation_repository.list_plans(farm_id=farm_id, limit=limit)
    return {"plans": items, "count": len(items)}


@router.get("/rehabilitation/plans/{plan_id}")
def rehabilitation_plan_record(plan_id: UUID) -> dict[str, Any]:
    item = rehabilitation_repository.get_plan(plan_id)
    if not item:
        raise CocoAidError(
            "Rehabilitation plan not found", status_code=404,
            details={"plan_id": str(plan_id)},
        )
    return item


@router.get("/decision-support/status")
def decision_support_status() -> dict[str, Any]:
    return {
        "engine": decision_support_engine.descriptor.model_dump(mode="json"),
        "parameter_version": DECISION_SUPPORT_PARAMETER_VERSION,
        "dependency_graph_version": DEPENDENCY_GRAPH_VERSION,
        "dependency_graph": DEPENDENCY_GRAPH,
        "storage": decision_support_repository.summary(),
        "failure_policies": ["continue_optional", "strict"],
        "data_notice": DECISION_SUPPORT_DATA_NOTICE,
        "safety_policy": {
            "overwrites_source_engines": False,
            "creates_new_field_evidence": False,
            "unverified_chemical_dosage_generated": False,
            "partial_runs_are_disclosed": True,
        },
    }


@router.post("/decision-support/compose")
def decision_support_compose(request: DecisionSupportRequest) -> dict[str, Any]:
    result = decision_support_engine.execute(request)
    return result.model_dump(mode="json")


@router.get("/decision-support/runs")
def decision_support_runs(
    farm_id: UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    items = decision_support_repository.list_runs(farm_id=farm_id, limit=limit)
    return {"runs": items, "count": len(items)}


@router.get("/decision-support/runs/{analysis_run_id}")
def decision_support_run_record(analysis_run_id: UUID) -> dict[str, Any]:
    item = decision_support_repository.get_run(analysis_run_id)
    if not item:
        raise CocoAidError(
            "Decision-support run not found", status_code=404,
            details={"analysis_run_id": str(analysis_run_id)},
        )
    return item

@router.get("/workflows/auto-phase9-10/status")
def auto_phase9_10_status() -> dict[str, Any]:
    return auto_phase_workflow_status()


@router.post("/workflows/auto-phase9-10/kick")
def auto_phase9_10_kick() -> dict[str, Any]:
    return kick_auto_phase_workflow(f"http://127.0.0.1:{settings.port}")


@router.post("/workflows/auto-phase9-10/bootstrap")
async def auto_phase9_10_bootstrap(farm: FarmCreate) -> dict[str, Any]:
    try:
        return await bootstrap_from_farm(farm, f"http://127.0.0.1:{settings.port}")
    except Exception as exc:
        raise CocoAidError(
            "Automatic Phase 9/10 preparation failed",
            status_code=503,
            details={"reason": str(exc)},
        ) from exc


@router.get("/coco-pilot/status")
def coco_pilot_status() -> dict[str, Any]:
    return {
        "service_id": "v3.coco_pilot",
        "version": COCO_PILOT_ENGINE_VERSION,
        "availability": "available",
        "maturity": "experimental",
        "parameter_version": COCO_PILOT_PARAMETER_VERSION,
        "prompt_version": COCO_PILOT_PROMPT_VERSION,
        "modes": [
            "explain_result", "compare_scenarios", "work_plan",
            "risk_summary", "uncertainty", "report_narrative",
        ],
        "providers": {
            "deterministic": "Always available and used by default.",
            "gemini_if_configured": assistant_status(),
        },
        "formal_report_generator_version": FORMAL_REPORT_GENERATOR_VERSION,
        "formal_report_formats": ["docx", "pdf"],
        "storage": coco_pilot_repository.summary(),
        "safety_policy": {
            "farmer_names_sent_to_provider": False,
            "restricted_raw_records_sent_to_provider": False,
            "creates_new_field_evidence": False,
            "overrides_analytical_results": False,
            "unverified_chemical_dosage_generated": False,
            "numeric_tables_generated_by_llm": False,
            "provider_failure_blocks_core_analysis": False,
        },
        "data_notice": FORMAL_REPORT_DATA_NOTICE,
    }


@router.post("/coco-pilot/explain")
async def coco_pilot_explain(request: CocoPilotRequest) -> dict[str, Any]:
    try:
        result = await coco_pilot_service.explain(request)
    except FileNotFoundError as exc:
        raise CocoAidError(str(exc), status_code=404) from exc
    return result.model_dump(mode="json")


@router.get("/coco-pilot/runs")
def coco_pilot_runs(
    analysis_run_id: UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    items = coco_pilot_repository.list_responses(analysis_run_id=analysis_run_id, limit=limit)
    return {"runs": items, "count": len(items)}


@router.get("/coco-pilot/runs/{run_id}")
def coco_pilot_run_record(run_id: UUID) -> dict[str, Any]:
    item = coco_pilot_repository.get_response(run_id)
    if not item:
        raise CocoAidError("CoCO-PILOT run not found", status_code=404, details={"run_id": str(run_id)})
    return item


@router.post("/formal-reports/generate")
def formal_report_generate(request: FormalReportRequest) -> dict[str, Any]:
    try:
        record, _ = generate_formal_report(request)
    except FileNotFoundError as exc:
        raise CocoAidError(str(exc), status_code=404) from exc
    except ValueError as exc:
        raise CocoAidError(str(exc), status_code=422) from exc
    payload = record.model_dump(mode="json")
    payload["download_url"] = f"{settings.v2_api_prefix}/formal-reports/{record.report_id}/download"
    return payload


@router.get("/formal-reports")
def formal_report_list(
    analysis_run_id: UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    items = coco_pilot_repository.list_reports(analysis_run_id=analysis_run_id, limit=limit)
    return {"reports": items, "count": len(items)}


@router.get("/formal-reports/{report_id}")
def formal_report_record(report_id: UUID) -> dict[str, Any]:
    item = coco_pilot_repository.get_report(report_id)
    if not item:
        raise CocoAidError("Formal report not found", status_code=404, details={"report_id": str(report_id)})
    item.pop("filepath", None)
    item["download_url"] = f"{settings.v2_api_prefix}/formal-reports/{report_id}/download"
    return item


@router.get("/formal-reports/{report_id}/download")
def formal_report_download(report_id: UUID):
    item = coco_pilot_repository.get_report(report_id)
    if not item:
        raise CocoAidError("Formal report not found", status_code=404, details={"report_id": str(report_id)})
    path = Path(item["filepath"]).resolve()
    root = settings.reports_dir.resolve()
    if root not in path.parents or not path.exists():
        raise CocoAidError("Formal report file is unavailable", status_code=404, details={"report_id": str(report_id)})
    media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if item["report_format"] == "docx" else "application/pdf"
    return FileResponse(path, filename=item["filename"], media_type=media_type)

