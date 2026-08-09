from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from uuid import UUID

from app.bayesian import BAYESIAN_PARAMETER_VERSION, run_particle_filter
from app.bayesian.particle_filter import ParticleFilterInputs
from app.bayesian import repository
from app.core.errors import EngineExecutionError
from app.domain.bayesian import (
    BayesianEngineOutput,
    BayesianEvidenceObservation,
    BayesianPosterior,
    BayesianSimulationRequest,
    PalmStateVector,
)
from app.domain.enums import EngineAvailability, EngineMaturity
from app.domain.provenance import RunProvenance, VersionReference
from app.engines.base import AnalyticalEngine, EngineDescriptor, EngineExecutionContext
from app.engines.registry import engine_registry
from app.production import repository as production_repository

BAYESIAN_ENGINE_VERSION = "1.0.0"
BAYESIAN_DATA_NOTICE = (
    "This Phase 5 posterior is an experimental particle-filter simulation. Transition rates and prior distributions "
    "are transparent development assumptions pending longitudinal farm calibration and expert review. Only farmer-reported, "
    "field-confirmed, or expert-confirmed observations can update particle weights; predicted and suspected observations "
    "are retained for traceability but are not assimilated as evidence."
)

BAYESIAN_DESCRIPTOR = EngineDescriptor(
    engine_id="v3.bayesian",
    name="Bayesian Farm-State Simulator",
    version=BAYESIAN_ENGINE_VERSION,
    maturity=EngineMaturity.EXPERIMENTAL,
    availability=EngineAvailability.AVAILABLE,
    input_contract="BayesianSimulationRequest",
    output_contract="BayesianEngineOutput",
    deterministic_with_seed=True,
    dependencies=["v3.production", "v3.weather_assimilation", "bayesian_parameter_registry"],
    limitations=[
        "Transition rates and parameter priors require field calibration",
        "Weather-history features are archived forecast reference data rather than station observations",
        "Posterior particles are summarized rather than stored individually",
        "Monthly dynamics are experimental and are not official PCA diagnoses",
    ],
)


def _feature_map(snapshot: dict) -> dict[str, float | int | str]:
    value = snapshot.get("features")
    if not isinstance(value, dict):
        raise EngineExecutionError("Production feature snapshot is malformed")
    return value


def _climate_context(features: dict[str, float | int | str]) -> tuple[float, float, float]:
    def number(name: str, default: float = 0.0) -> float:
        value = features.get(name, default)
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    dry = min(max(number("consecutive_dry_days") / 30.0, 0.0), 1.0)
    heat = max(
        min(max(number("forecast_heat_stress_days_16d") / 16.0, 0.0), 1.0),
        min(max(number("heat_stress_days_30d") / 30.0, 0.0), 1.0),
    )
    wind = min(max(number("forecast_max_wind_gust_16d_kmh") / 150.0, 0.0), 1.0)
    moisture_balance = number("moisture_balance_30d_mm")
    deficit = min(max(-moisture_balance / 200.0, 0.0), 1.0)
    climate_stress = min(max(0.35 * dry + 0.25 * heat + 0.20 * wind + 0.20 * deficit, 0.0), 1.0)
    rainfall = max(number("forecast_rainfall_16d_mm"), 0.0)
    moisture_index = min(max(moisture_balance / 200.0, -1.0), 1.0)
    return climate_stress, rainfall, moisture_index


class BayesianEngine(AnalyticalEngine[BayesianSimulationRequest, BayesianEngineOutput]):
    descriptor = BAYESIAN_DESCRIPTOR
    input_model = BayesianSimulationRequest
    output_model = BayesianEngineOutput

    def __init__(self, *, database_path: Path | None = None):
        self.database_path = database_path

    def _initial_state_and_prior(
        self, payload: BayesianSimulationRequest, forecast: dict
    ) -> tuple[PalmStateVector, dict[str, dict[str, float]], UUID | None]:
        if payload.initial_state is not None:
            return payload.initial_state, {}, None
        prior = repository.get_posterior(payload.prior_posterior_id, database_path=self.database_path)
        if not prior:
            raise EngineExecutionError("Prior Bayesian posterior was not found")
        if prior["farm_id"] != forecast["farm_id"]:
            raise EngineExecutionError("Prior posterior and production forecast belong to different farms")
        if prior.get("cell_id") and forecast.get("cell_id") and prior["cell_id"] != forecast["cell_id"]:
            raise EngineExecutionError("Prior posterior and production forecast belong to different farm cells")
        state = PalmStateVector.model_validate(prior["state"])
        parameter_prior = repository.prior_parameter_summaries(
            payload.prior_posterior_id, database_path=self.database_path,
        )
        return state, parameter_prior, UUID(str(payload.prior_posterior_id))

    def _evidence(
        self, payload: BayesianSimulationRequest, forecast: dict
    ) -> list[BayesianEvidenceObservation]:
        rows = repository.get_observations(payload.evidence_observation_ids, database_path=self.database_path)
        if len(rows) != len(payload.evidence_observation_ids):
            found = {row["id"] for row in rows}
            missing = [str(item) for item in payload.evidence_observation_ids if str(item) not in found]
            raise EngineExecutionError("One or more Bayesian evidence observations were not found", details={"missing": missing})
        observations = [BayesianEvidenceObservation.model_validate({
            "observation_id": row["id"],
            "farm_id": row["farm_id"],
            "cell_id": row["cell_id"],
            "production_forecast_id": row["production_forecast_id"],
            "evidence_type": row["evidence_type"],
            "evidence_status": row["evidence_status"],
            "observed_at": row["observed_at"],
            "value": row["value"],
            "unit": row["unit"],
            "notes": row["notes"],
            "source_label": row["source_label"],
            "created_at": row["created_at"],
        }) for row in rows]
        for observation in observations:
            if str(observation.farm_id) != forecast["farm_id"]:
                raise EngineExecutionError(
                    "Bayesian evidence belongs to a different farm",
                    details={"observation_id": str(observation.observation_id)},
                )
            if observation.production_forecast_id and str(observation.production_forecast_id) != forecast["id"]:
                raise EngineExecutionError(
                    "Bayesian evidence is linked to a different production forecast",
                    details={"observation_id": str(observation.observation_id)},
                )
        return observations

    def _run(self, payload: BayesianSimulationRequest, context: EngineExecutionContext):
        forecast = production_repository.get_forecast(
            payload.production_forecast_id, database_path=self.database_path,
        )
        if not forecast:
            raise EngineExecutionError("Production forecast was not found")
        base_production = forecast.get("variety_adjusted_prediction") or forecast.get("raw_ml_prediction")
        if base_production is None or float(base_production) < 0:
            raise EngineExecutionError("Production forecast has no valid baseline prediction")
        snapshot = production_repository.get_feature_snapshot(
            forecast["feature_snapshot_id"], database_path=self.database_path,
        )
        if not snapshot:
            raise EngineExecutionError("Production feature snapshot was not found")
        features = _feature_map(snapshot)
        initial_state, prior_parameters, prior_id = self._initial_state_and_prior(payload, forecast)
        evidence = self._evidence(payload, forecast)
        climate_stress, forecast_rainfall, moisture_index = _climate_context(features)
        base_pest = min(max(float(features.get("pest_probability", 0.15)), 0.0), 1.0)

        result = run_particle_filter(ParticleFilterInputs(
            initial_state=initial_state,
            base_production_tonnes=float(base_production),
            base_pest_probability=base_pest,
            climate_stress_index=climate_stress,
            forecast_rainfall_mm=forecast_rainfall,
            moisture_balance_index=moisture_index,
            intervention=payload.intervention,
            horizon_months=payload.horizon_months,
            particle_count=payload.particle_count,
            random_seed=payload.random_seed,
            evidence=evidence,
            prior_parameter_summaries=prior_parameters,
            prior_posterior_id=str(prior_id) if prior_id else None,
        ))
        weather_run_id = UUID(snapshot["weather_run_id"])
        warnings = list(dict.fromkeys(result.warnings))
        provenance = RunProvenance(
            farm_data_version=payload.farm_data_version,
            weather_run_id=weather_run_id,
            model_versions=[
                VersionReference(component="production_model", version=forecast["model_version"]),
                VersionReference(component="bayesian_engine", version=BAYESIAN_ENGINE_VERSION),
            ],
            parameter_versions=[
                VersionReference(component="bayesian_parameters", version=BAYESIAN_PARAMETER_VERSION),
            ],
            feature_adapter_version=forecast["feature_adapter_version"],
            simulation_seed=payload.random_seed,
            simulation_count=payload.particle_count,
            warnings=warnings,
            limitations=[
                "Posterior transitions and priors require longitudinal field calibration.",
                "Particle histories are summarized to preserve storage efficiency.",
                "The output is decision support, not an official diagnosis or guaranteed yield.",
            ],
        )
        posterior = BayesianPosterior(
            farm_id=UUID(forecast["farm_id"]),
            cell_id=UUID(forecast["cell_id"]) if forecast.get("cell_id") else None,
            production_forecast_id=payload.production_forecast_id,
            prior_posterior_id=prior_id,
            valid_at=payload.baseline_state_date + timedelta(days=30 * payload.horizon_months),
            horizon_months=payload.horizon_months,
            state=result.state,
            state_intervals=result.state_intervals,
            parameters=result.parameters,
            production_distribution=result.production_distribution,
            base_production_tonnes=float(base_production),
            probability_of_decline=result.probability_of_decline,
            probability_of_recovery=result.probability_of_recovery,
            probability_of_tree_mortality=result.probability_of_tree_mortality,
            probability_of_pest_outbreak=result.probability_of_pest_outbreak,
            primary_uncertainty_sources=result.uncertainty_sources,
            evidence_observation_ids=[item.observation_id for item in evidence],
            provenance=provenance,
        )
        output = BayesianEngineOutput(
            posterior=posterior,
            evidence_results=result.evidence_results,
            diagnostics=result.diagnostics,
            data_notice=BAYESIAN_DATA_NOTICE,
            warnings=warnings,
        )
        repository.save_output(
            output,
            baseline_state_date=payload.baseline_state_date,
            intervention=payload.intervention.value,
            database_path=self.database_path,
        )
        return output, warnings


bayesian_engine = BayesianEngine()
engine_registry.register(bayesian_engine)

__all__ = ["BAYESIAN_DESCRIPTOR", "BAYESIAN_ENGINE_VERSION", "BayesianEngine", "bayesian_engine"]
