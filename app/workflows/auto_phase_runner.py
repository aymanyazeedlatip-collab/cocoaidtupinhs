from __future__ import annotations

import subprocess
import asyncio
import sys
import threading
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

import httpx

ROOT = Path(__file__).resolve().parents[2]
_LOCK = threading.Lock()
_THREAD: threading.Thread | None = None
_STATUS: dict[str, Any] = {
    "state": "idle",
    "phase9": "Waiting",
    "phase10": "Waiting",
    "message": "Waiting for an eligible production forecast.",
    "latest_forecast_id": None,
    "analysis_run_id": None,
    "last_run_at": None,
    "last_error": None,
}


def workflow_status() -> dict[str, Any]:
    with _LOCK:
        return deepcopy(_STATUS)


def _update(**values: Any) -> None:
    with _LOCK:
        _STATUS.update(values)


def _json(client: httpx.Client, path: str) -> dict[str, Any]:
    response = client.get(path)
    response.raise_for_status()
    return response.json()


def _run_script(script: str, *args: str, timeout: int = 480) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(ROOT / "scripts" / script), *args]
    return subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _latest_decision_for_forecast(client: httpx.Client, farm_id: str, forecast_id: str) -> dict[str, Any] | None:
    runs = _json(client, f"/api/v2/decision-support/runs?farm_id={farm_id}&limit=25").get("runs", [])
    return next((item for item in runs if str(item.get("production_forecast_id")) == forecast_id), None)


def _phase10_complete(client: httpx.Client, analysis_run_id: str) -> bool:
    pilot = _json(client, f"/api/v2/coco-pilot/runs?analysis_run_id={analysis_run_id}&limit=10")
    reports = _json(client, f"/api/v2/formal-reports?analysis_run_id={analysis_run_id}&limit=10")
    return int(pilot.get("count", 0)) >= 1 and int(reports.get("count", 0)) >= 2


def run_once(base_url: str = "http://127.0.0.1:8000") -> None:
    now = datetime.now(UTC).isoformat()
    _update(state="checking", phase9="Checking", phase10="Waiting", message="Checking the newest production forecast and evidence records…", last_error=None)
    try:
        with httpx.Client(base_url=base_url.rstrip("/"), timeout=45.0) as client:
            forecasts = _json(client, "/api/v2/production/forecasts?limit=1").get("forecasts", [])
            if not forecasts:
                _update(state="waiting", phase9="Waiting for forecast", phase10="Waiting", message="Run a farm forecast first. Phase 9 and Phase 10 will start automatically afterward.")
                return
            forecast = forecasts[0]
            forecast_id = str(forecast["id"])
            farm_id = str(forecast["farm_id"])
            _update(latest_forecast_id=forecast_id)

            decision = _latest_decision_for_forecast(client, farm_id, forecast_id)
            if decision is None:
                observations = _json(client, f"/api/v2/pests/observations?farm_id={farm_id}&limit=1").get("observations", [])
                observation_id = str(observations[0]["id"]) if observations else None
                _update(state="running", phase9="Running", phase10="Waiting", message="Phase 9 is composing pest, intercropping, rehabilitation, and decision-support records…")
                args = ["--production-forecast-id", forecast_id, "--base-url", base_url, "--all-intercrops"]
                if observation_id:
                    args.extend(["--observation-id", observation_id])
                result = _run_script("run_phase9_workflow.py", *args)
                if result.returncode != 0:
                    detail = (result.stderr or result.stdout or "Phase 9 workflow failed").strip()[-2500:]
                    raise RuntimeError(detail)
                decision = _latest_decision_for_forecast(client, farm_id, forecast_id)
                if decision is None:
                    raise RuntimeError("Phase 9 completed without a retrievable decision-support record.")
            analysis_run_id = str(decision["analysis_run_id"])
            _update(phase9="Complete", analysis_run_id=analysis_run_id, message="Phase 9 is complete. Checking Phase 10 outputs…")

            if _phase10_complete(client, analysis_run_id):
                _update(state="complete", phase10="Complete", message="Phase 9 and Phase 10 are complete for the latest eligible forecast.", last_run_at=now)
                return

            _update(state="running", phase10="Running", message="Phase 10 is generating the grounded CoCO-PILOT narrative and formal reports…")
            result = _run_script(
                "run_phase10_workflow.py",
                "--analysis-run-id", analysis_run_id,
                "--base-url", base_url,
            )
            if result.returncode != 0:
                detail = (result.stderr or result.stdout or "Phase 10 workflow failed").strip()[-2500:]
                raise RuntimeError(detail)
            _update(state="complete", phase10="Complete", message="Phase 9 and Phase 10 completed automatically for the latest eligible forecast.", last_run_at=now)
    except Exception as exc:  # pragma: no cover - runtime resilience path
        _update(state="error", message="Automatic workflow paused after an error. Core farm analysis remains available.", last_error=str(exc), last_run_at=now)
        with _LOCK:
            if _STATUS.get("phase9") == "Running":
                _STATUS["phase9"] = "Error"
            if _STATUS.get("phase10") == "Running":
                _STATUS["phase10"] = "Error"


def kick(base_url: str = "http://127.0.0.1:8000") -> dict[str, Any]:
    global _THREAD
    with _LOCK:
        if _THREAD is not None and _THREAD.is_alive():
            return deepcopy(_STATUS)
        _THREAD = threading.Thread(target=run_once, args=(base_url,), daemon=True, name="cocoaid-auto-phase9-10")
        _THREAD.start()
        return deepcopy(_STATUS)


async def bootstrap_from_farm(farm: Any, base_url: str = "http://127.0.0.1:8000") -> dict[str, Any]:
    """Create the Phase 9-compatible v3 production record directly from the farm used by the legacy long-term forecast.

    The visible forecast endpoint predates the Phase 9/10 repository contracts. Without this bridge,
    generating a forecast in the UI does not create a v3 production_forecast record, so the automatic
    runner has nothing eligible to process. This function persists a fresh weather feature set and a
    matching v3 production forecast, then kicks the normal Phase 9/10 runner.
    """
    from app.domain.production import ProductionEngineRequest
    from app.engines.production import production_engine
    from app.schemas.weather_assimilation import WeatherAssimilationRequest
    from app.weather.assimilation.service import assimilate_weather

    latitude = float(farm.location.latitude)
    longitude = float(farm.location.longitude)
    farm_key = "|".join([
        str(farm.name).strip().lower(),
        f"{latitude:.6f}", f"{longitude:.6f}",
        str(farm.location.province).strip().lower(), str(farm.location.municipality).strip().lower(),
        f"{float(farm.area_hectares):.4f}",
    ])
    farm_id = uuid5(NAMESPACE_URL, f"cocoaid-farm:{farm_key}")
    _update(state="checking", phase9="Preparing", phase10="Waiting", message="Registering the new farm forecast for automatic Phase 9 and Phase 10…", last_error=None)

    weather = await assimilate_weather(WeatherAssimilationRequest(
        latitude=latitude,
        longitude=longitude,
        model="auto",
        forecast_days=16,
        history_days=90,
        farm_id=farm_id,
        force_refresh=False,
    ))
    feature_set = weather.get("feature_set") or {}
    feature_set_id = feature_set.get("id") or feature_set.get("feature_set_id")
    if not feature_set_id:
        raise RuntimeError("Weather assimilation completed without a feature-set identifier.")

    soil = farm.soil_terrain
    nutrient = max(0.0, min(1.0, (float(soil.nitrogen_index) + float(soil.phosphorus_index) + float(soil.potassium_index)) / 3.0))
    ph_fit = max(0.0, 1.0 - abs(float(soil.soil_ph) - 6.2) / 3.0)
    suitability_score = max(0.05, min(0.98, 0.35 * nutrient + 0.35 * float(soil.drainage_index) + 0.30 * ph_fit))
    symptoms = farm.symptoms
    symptom_count = sum(bool(value) for key, value in symptoms.model_dump().items() if key != "severity")
    pest_probability = max(0.02, min(0.90, 0.06 + 0.055 * symptom_count + 0.07 * float(symptoms.severity) + 0.06 * (1.0 - float(soil.drainage_index))))
    baseline = float(farm.production.annual_production_tons)
    trees = farm.trees
    request = ProductionEngineRequest(
        farm_id=farm_id,
        farm_data_version="legacy-long-term-forecast-bridge-1.0.0",
        weather_feature_set_id=feature_set_id,
        farm_area_hectares=float(farm.area_hectares),
        productive_trees=int(trees.productive),
        aging_trees=int(trees.aging),
        stressed_trees=int(trees.stressed),
        infested_trees=int(trees.infested),
        recovering_trees=int(trees.recovering),
        soil_ph=float(soil.soil_ph),
        nitrogen_index=float(soil.nitrogen_index),
        phosphorus_index=float(soil.phosphorus_index),
        potassium_index=float(soil.potassium_index),
        suitability_score=suitability_score,
        pest_probability=pest_probability,
        variety_class=str(trees.variety),
        intervention="none",
        baseline_annual_production_tons=baseline if baseline > 0 else None,
        young_nut_share=0.03,
    )
    output = await asyncio.to_thread(production_engine.execute, request)
    forecast_id = str(output.output.forecast.production_forecast_id if hasattr(output, "output") else output.forecast.production_forecast_id)
    _update(latest_forecast_id=forecast_id, phase9="Queued", phase10="Waiting", message="Forecast registered. Phase 9 is starting automatically now…")
    workflow = kick(base_url)
    return {"farm_id": str(farm_id), "production_forecast_id": forecast_id, "workflow": workflow}
