from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from app.core.errors import EngineExecutionError
from app.domain.enums import EngineAvailability, EngineMaturity, ForecastHorizonType, ProductType
from app.domain.production import (
    ProductionEngineOutput, ProductionEngineRequest, ProductionForecast, ProductionShadowComparison,
)
from app.domain.provenance import RunProvenance, VersionReference
from app.domain.units import UnitCode
from app.engines.base import AnalyticalEngine, EngineDescriptor, EngineExecutionContext
from app.engines.registry import engine_registry
from app.models.registry import model_metadata, predict
from app.production.conversions import (
    VARIETY_PARAMETER_VERSION, build_product_estimates, load_variety_parameters, variety_adjustment_factor,
)
from app.production.feature_adapter import PRODUCTION_FEATURE_ADAPTER_VERSION, build_feature_snapshot
from app.production import repository
from app.weather.assimilation import repository as weather_repository

PRODUCTION_ENGINE_VERSION = "1.0.0"
PRODUCTION_DATA_NOTICE = (
    "The retained production model was trained on synthetic/reference-based development data and requires field validation. "
    "Weather-history inputs from the forecast API are archived forecast values rather than station observations. "
    "Named-variety adjustments and product conversions use PCA reference parameters and are not Bayesian posterior results."
)

PRODUCTION_DESCRIPTOR = EngineDescriptor(
    engine_id="v3.production",
    name="Versioned Coconut Production Engine",
    version=PRODUCTION_ENGINE_VERSION,
    maturity=EngineMaturity.EXPERIMENTAL,
    availability=EngineAvailability.AVAILABLE,
    input_contract="ProductionEngineRequest",
    output_contract="ProductionEngineOutput",
    dependencies=["legacy.production", "v3.weather_assimilation", "variety_parameter_registry"],
    limitations=[
        "Retained model uses synthetic/reference-based training data",
        "Weather history is archived forecast reference data",
        "Named-variety adjustment is bounded and requires field calibration",
        "Bayesian posterior is not generated in Phase 4",
    ],
)


class ProductionEngine(AnalyticalEngine[ProductionEngineRequest, ProductionEngineOutput]):
    descriptor = PRODUCTION_DESCRIPTOR
    input_model = ProductionEngineRequest
    output_model = ProductionEngineOutput

    def __init__(self, *, database_path: Path | None = None):
        self.database_path = database_path

    def _run(self, payload: ProductionEngineRequest, context: EngineExecutionContext):
        # Resolve a named PCA variety before adapting features so the retained model
        # receives the correct legacy Tall/Dwarf/Hybrid category.
        variety, params, variety_warnings = load_variety_parameters(
            payload.variety_id, payload.variety_class, database_path=self.database_path,
        )
        resolved_class = payload.variety_class
        resolved_id = None
        if variety:
            resolved_id = variety["id"]
            resolved_class = {"tall": "Tall", "dwarf": "Dwarf", "hybrid": "Hybrid"}[variety["variety_class"]]
        from app.domain.production import LegacyVarietyClass
        resolved_class_enum = LegacyVarietyClass(resolved_class)
        adapter_payload = payload.model_copy(update={"variety_class": resolved_class_enum})

        snapshot = build_feature_snapshot(adapter_payload, database_path=self.database_path)
        raw = predict("production", snapshot.features)
        if raw is None or raw < 0:
            raise EngineExecutionError("The retained production model could not produce a valid prediction")
        metadata = model_metadata("production")["production"]
        factor, factor_basis, factor_warnings = variety_adjustment_factor(
            variety, params, resolved_class_enum, database_path=self.database_path,
        )
        adjusted = float(raw) * factor
        products, conversion_warnings = build_product_estimates(
            adjusted, params, young_nut_share=payload.young_nut_share,
        )
        weather_run = weather_repository.get_run(snapshot.weather_run_id, database_path=self.database_path)
        if not weather_run:
            raise EngineExecutionError("Weather run disappeared during production execution")
        valid_from = datetime.fromisoformat(weather_run["valid_from"])
        valid_to = datetime.fromisoformat(weather_run["valid_to"])
        if valid_to - valid_from > timedelta(days=16):
            valid_to = valid_from + timedelta(days=16)
        provenance = RunProvenance(
            farm_data_version=payload.farm_data_version,
            weather_run_id=snapshot.weather_run_id,
            model_versions=[VersionReference(
                component="production_model", version=metadata["version"], sha256=metadata["artifact"]["sha256"],
            )],
            parameter_versions=[VersionReference(component="variety_parameters", version=VARIETY_PARAMETER_VERSION)],
            feature_adapter_version=PRODUCTION_FEATURE_ADAPTER_VERSION,
            warnings=snapshot.warnings + variety_warnings + factor_warnings + conversion_warnings,
            limitations=[PRODUCTION_DATA_NOTICE],
        )
        forecast = ProductionForecast(
            farm_id=payload.farm_id, cell_id=payload.cell_id,
            product=ProductType.WHOLE_NUT_WITH_HUSK,
            horizon_type=ForecastHorizonType.LIVE_NUMERICAL,
            valid_from=valid_from, valid_to=valid_to,
            unit=UnitCode.TONNE,
            raw_ml_prediction=float(raw), variety_adjusted_prediction=adjusted,
            posterior_prediction=None, posterior_status="not_run",
            model_version=metadata["version"], feature_adapter_version=PRODUCTION_FEATURE_ADAPTER_VERSION,
            feature_snapshot_id=snapshot.feature_snapshot_id,
            variety_id=resolved_id, variety_class=resolved_class_enum,
            variety_adjustment_factor=factor, variety_adjustment_basis=factor_basis, product_estimates=products,
            provenance=provenance,
        )
        if payload.baseline_annual_production_tons:
            baseline = payload.baseline_annual_production_tons
            ratio = min(1.35, max(0.65, float(raw) / baseline))
            legacy = baseline * (0.90 + 0.10 * ratio)
            shadow = ProductionShadowComparison(
                status="available", legacy_prediction_tons=legacy,
                v3_raw_prediction_tons=float(raw), v3_variety_adjusted_prediction_tons=adjusted,
                raw_delta_tons=float(raw) - legacy, adjusted_delta_tons=adjusted - legacy,
                legacy_method=(
                    "Reproduces the v2.11 simulation-context correction: baseline annual production multiplied by "
                    "0.90 + 0.10 * clip(model_prediction / baseline, 0.65, 1.35)."
                ),
            )
        else:
            shadow = ProductionShadowComparison(
                status="not_available", v3_raw_prediction_tons=float(raw),
                v3_variety_adjusted_prediction_tons=adjusted,
                legacy_method="Provide baseline_annual_production_tons to reproduce the v2.11 bounded correction for shadow comparison.",
            )
        warnings = list(dict.fromkeys(snapshot.warnings + variety_warnings + factor_warnings + conversion_warnings))
        output = ProductionEngineOutput(
            forecast=forecast, feature_snapshot=snapshot, shadow_comparison=shadow,
            data_notice=PRODUCTION_DATA_NOTICE, warnings=warnings,
        )
        repository.save_output(output, database_path=self.database_path)
        return output, warnings


production_engine = ProductionEngine()
engine_registry.register(production_engine)

__all__ = ["PRODUCTION_DESCRIPTOR", "PRODUCTION_ENGINE_VERSION", "ProductionEngine", "production_engine"]
