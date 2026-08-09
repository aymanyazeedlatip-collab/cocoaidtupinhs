from __future__ import annotations

from uuid import uuid4

from app.data_foundation.seeding import seed_reference_data
from app.domain.production import ProductionEngineRequest
from app.weather.assimilation.features import build_weather_feature_set
from app.weather.assimilation.normalizer import normalize_open_meteo_payload
from app.weather.assimilation.repository import save_run
from tests.weather_factory import RETRIEVED_AT, make_open_meteo_payload


def prepare_phase4_weather(*, database_path=None, rain_adjustment: float = 0.0) -> tuple[str, str]:
    normalized = normalize_open_meteo_payload(
        make_open_meteo_payload(forecast_rain_adjustment=rain_adjustment),
        model="auto",
        forecast_days=16,
        history_days=90,
        retrieved_at=RETRIEVED_AT,
    )
    run_id, feature_set_id, _ = save_run(
        normalized,
        build_weather_feature_set(normalized),
        database_path=database_path,
    )
    assert feature_set_id is not None
    return run_id, feature_set_id


def prepare_phase4_foundation(*, database_path=None) -> None:
    seed_reference_data(database_path=database_path)


def production_request(feature_set_id: str, **updates):
    payload = {
        "farm_id": uuid4(),
        "weather_feature_set_id": feature_set_id,
        "farm_area_hectares": 5.0,
        "productive_trees": 320,
        "aging_trees": 40,
        "stressed_trees": 20,
        "infested_trees": 5,
        "recovering_trees": 10,
        "soil_ph": 6.1,
        "nitrogen_index": 0.65,
        "phosphorus_index": 0.60,
        "potassium_index": 0.70,
        "suitability_score": 0.78,
        "pest_probability": 0.12,
        "variety_id": "agdt",
        "variety_class": "Unknown",
        "intervention": "none",
        "baseline_annual_production_tons": 25.0,
        "young_nut_share": 0.03,
    }
    payload.update(updates)
    return ProductionEngineRequest.model_validate(payload)
