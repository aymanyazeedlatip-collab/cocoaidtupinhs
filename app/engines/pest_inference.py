from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.bayesian import repository as bayesian_repository
from app.core.errors import EngineExecutionError
from app.domain.enums import EngineAvailability, EngineMaturity
from app.domain.pest import PestAssessmentRequest, PestAssessmentSummary, PestEngineOutput
from app.engines.base import AnalyticalEngine, EngineDescriptor, EngineExecutionContext
from app.engines.registry import engine_registry
from app.pest.inference import evaluate_pest_profile
from app.pest.parameters import PEST_PARAMETER_VERSION, SUPPORTED_PEST_IDS
from app.pest import repository
from app.production import repository as production_repository
from app.weather.assimilation import repository as weather_repository

PEST_ENGINE_VERSION = "1.0.0"
PEST_DATA_NOTICE = (
    "This Phase 6 engine converts PCA qualitative pest and disease references into transparent probabilistic "
    "inspection-priority assessments. PCA sources do not provide calibrated farm prevalence priors, likelihood ratios, "
    "spatial-decay constants, or loss coefficients; those values are versioned development assumptions pending expert "
    "review and georeferenced field calibration. Results are not laboratory diagnoses or pesticide prescriptions."
)
PEST_TAXONOMY_NOTICE = (
    "The supported palm-weevil profile is the PCA-referenced Asiatic palm weevil. It is intentionally separate from the "
    "legacy red palm weevil profile; the two are not merged without expert taxonomic reconciliation."
)

PEST_DESCRIPTOR = EngineDescriptor(
    engine_id="v3.pest_inference",
    name="PCA Pest-Specific Risk Inference Engine",
    version=PEST_ENGINE_VERSION,
    maturity=EngineMaturity.EXPERIMENTAL,
    availability=EngineAvailability.AVAILABLE,
    input_contract="PestAssessmentRequest",
    output_contract="PestEngineOutput",
    dependencies=["v3.weather_assimilation", "v3.production", "v3.bayesian", "pest_profile_registry"],
    limitations=[
        "Qualitative PCA rules require calibrated likelihood ratios and local prevalence data",
        "Output indicates outbreak plausibility and inspection priority, not confirmed diagnosis",
        "Expected losses across pests overlap and are not independent additive realized losses",
        "Only PCA-supported management text is returned; chemical dosage is intentionally excluded",
    ],
)


class PestInferenceEngine(AnalyticalEngine[PestAssessmentRequest, PestEngineOutput]):
    descriptor = PEST_DESCRIPTOR
    input_model = PestAssessmentRequest
    output_model = PestEngineOutput

    def __init__(self, *, database_path: Path | None = None):
        self.database_path = database_path

    def _run(self, payload: PestAssessmentRequest, context: EngineExecutionContext):
        forecast = production_repository.get_forecast(payload.production_forecast_id, database_path=self.database_path)
        if not forecast:
            raise EngineExecutionError(
                "Production forecast not found",
                details={"production_forecast_id": str(payload.production_forecast_id)},
            )
        if forecast["farm_id"] != str(payload.farm_id):
            raise EngineExecutionError("Pest request farm_id does not match the production forecast")
        if payload.cell_id and forecast.get("cell_id") and forecast["cell_id"] != str(payload.cell_id):
            raise EngineExecutionError("Pest request cell_id does not match the production forecast")

        snapshot = production_repository.get_feature_snapshot(forecast["feature_snapshot_id"], database_path=self.database_path)
        if not snapshot:
            raise EngineExecutionError("Production feature snapshot not found")
        feature_set = weather_repository.get_feature_set(snapshot["weather_feature_set_id"], database_path=self.database_path)
        if not feature_set:
            raise EngineExecutionError("Weather feature set linked to production forecast not found")

        baseline = float(forecast["variety_adjusted_prediction"])
        if payload.posterior_id:
            posterior = bayesian_repository.get_posterior(payload.posterior_id, database_path=self.database_path)
            if not posterior:
                raise EngineExecutionError("Bayesian posterior not found", details={"posterior_id": str(payload.posterior_id)})
            if posterior["farm_id"] != str(payload.farm_id):
                raise EngineExecutionError("Bayesian posterior farm_id does not match the pest request")
            if posterior["production_forecast_id"] != str(payload.production_forecast_id):
                raise EngineExecutionError("Bayesian posterior does not belong to the supplied production forecast")
            baseline = float(posterior["production_distribution"]["median"])

        requested = payload.pest_profile_ids or list(SUPPORTED_PEST_IDS)
        unknown = sorted(set(requested) - set(SUPPORTED_PEST_IDS))
        if unknown:
            raise EngineExecutionError(
                "Unsupported Phase 6 pest profile",
                details={"unsupported": unknown, "supported": list(SUPPORTED_PEST_IDS)},
            )
        profiles = repository.load_reference_profiles(requested, database_path=self.database_path)
        found = {item["id"] for item in profiles}
        missing = sorted(set(requested) - found)
        if missing:
            raise EngineExecutionError(
                "PCA pest reference profiles are not initialized",
                details={"missing_profiles": missing},
            )

        observations = repository.get_observations(payload.observation_ids, database_path=self.database_path)
        if len(observations) != len(set(payload.observation_ids)):
            found_ids = {item["id"] for item in observations}
            missing_ids = [str(item) for item in payload.observation_ids if str(item) not in found_ids]
            raise EngineExecutionError("One or more pest observations were not found", details={"missing": missing_ids})
        for observation in observations:
            if observation["farm_id"] != str(payload.farm_id):
                raise EngineExecutionError("Pest observation farm_id does not match the request")
            if observation["pest_profile_id"] not in requested:
                raise EngineExecutionError("Pest observation profile is outside the requested profile set")

        run_id = uuid4()
        assessments = [
            evaluate_pest_profile(
                request=payload,
                run_id=run_id,
                profile=profile,
                rules=profile["rules"],
                actions=profile["actions"],
                observations=observations,
                feature_set=feature_set,
                production_snapshot=snapshot,
                baseline_production_tonnes=baseline,
                weather_run_id=feature_set["weather_run_id"],
            )
            for profile in profiles
        ]
        assessments.sort(key=lambda item: item.outbreak_probability, reverse=True)
        confirmed = sum(
            1 for item in observations if item["evidence_status"] in {"field_confirmed", "expert_confirmed"}
        )
        highest = assessments[0]
        combined_expected = min(baseline, sum(item.expected_loss for item in assessments))
        warnings = [
            "Expected losses across pest profiles overlap; the combined summary is capped at baseline production and is not a joint-loss model.",
            "Development likelihood ratios and spatial-decay parameters require PCA/expert and field calibration.",
        ]
        output = PestEngineOutput(
            run_id=run_id,
            assessments=assessments,
            summary=PestAssessmentSummary(
                highest_probability=highest.outbreak_probability,
                highest_risk_pest_id=highest.profile.pest_profile_id,
                combined_expected_loss_tonnes=combined_expected,
                urgent_inspection_count=sum(item.risk_class in {"high", "critical"} for item in assessments),
                confirmed_evidence_count=confirmed,
            ),
            parameter_version=PEST_PARAMETER_VERSION,
            data_notice=PEST_DATA_NOTICE,
            warnings=warnings,
            taxonomy_notice=PEST_TAXONOMY_NOTICE,
            weather_feature_set_id=feature_set["id"],
            weather_run_id=feature_set["weather_run_id"],
            evidence_audit=[
                {
                    "observation_id": item["id"],
                    "pest_profile_id": item["pest_profile_id"],
                    "factor_code": item["factor_code"],
                    "evidence_status": item["evidence_status"],
                    "used_for_probability": item["evidence_status"] not in {"predicted", "suspected"},
                    "bayesian_observation_id": item.get("bayesian_observation_id"),
                }
                for item in observations
            ],
        )
        repository.save_output(
            output,
            request_payload={
                "farm_id": str(payload.farm_id),
                "cell_id": str(payload.cell_id) if payload.cell_id else None,
                "production_forecast_id": str(payload.production_forecast_id),
                "posterior_id": str(payload.posterior_id) if payload.posterior_id else None,
                "assessed_at": payload.assessed_at.isoformat(),
                "pest_profile_ids": requested,
                "context": payload.context.model_dump(mode="json"),
                "observation_ids": [str(item) for item in payload.observation_ids],
                "nearby_confirmed_cases": [item.model_dump(mode="json") for item in payload.nearby_confirmed_cases],
            },
            database_path=self.database_path,
        )
        return output, warnings


pest_inference_engine = PestInferenceEngine()
engine_registry.register(pest_inference_engine)

__all__ = [
    "PEST_DESCRIPTOR", "PEST_ENGINE_VERSION", "PEST_DATA_NOTICE", "PEST_TAXONOMY_NOTICE",
    "PestInferenceEngine", "pest_inference_engine",
]
