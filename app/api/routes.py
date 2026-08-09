from __future__ import annotations

import asyncio
import logging
from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from app.climate.projections import climate_projection, generate_annual_trajectory
from app.core.config import settings
from app.core.errors import ProviderRateLimitError, ProviderUnavailableError
from app.gis.analysis import farm_assessment, rehabilitation_grid, rehabilitation_event_plans
from app.models.registry import model_metadata
from app.reports.pdf import generate_pdf
from app.reports.docx import generate_docx
from app.data.official_production import metadata as official_metadata, province_names, public_profile
from app.schemas.analysis import (
    ClimateProjectionRequest, ClimateTrajectoryRequest, FarmSiteForecastRequest, FullAnalysisRequest, PestRiskRequest,
    PestSpecificRequest, ReportRequest, ScenarioComparisonRequest, SimulationRequest, SuitabilityRequest, ForecastSaveRequest, RehabilitationPlanRequest,
)
from app.schemas.farm import FarmCreate, FarmPatch
from app.schemas.weather import WeatherCubeRequest, WeatherFrameRequest, WeatherGridRequest, WeatherPointRequest
from app.schemas.assistant import AssistantChatRequest, AssistantKeyRequest
from app.services.analysis import full_analysis, pest_assessment, suitability_assessment
from app.services.supabase_state import supabase_state
from app.services.assistant import (
    assistant_status, attach_saved_report, chat_with_gemini, clear_api_key, save_api_key, store_uploaded_document,
)
from app.math.pest_specific import evaluate_specific_pests
from app.simulation.compare import compare_scenarios
from app.simulation.engine import run_simulation
from app.simulation.farm_site_forecast import farm_map_bounds, generate_farm_site_forecast
from app.storage.database import (
    create_farm, delete_farm, get_analysis, get_farm, get_report, list_farms, update_farm,
    list_analyses, delete_analysis, list_reports, save_forecast, list_forecasts,
    get_forecast, delete_forecast, database_summary, report_record,
)
from app.weather.providers import active_storms, geocode, point_forecast, radar_frames, weather_cube, weather_grid

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)


@router.get("/health")
def health() -> dict:
    state_status = supabase_state.status()
    persistent = bool(settings.supabase_state_configured or settings.persistent_data_dir is not None)
    return {
        "status": "healthy", "project": settings.app_name, "environment": settings.environment,
        "api_version": settings.api_version, "offline_mode": settings.offline_mode,
        "persistent_storage_configured": persistent,
        "storage_mode": "supabase_storage" if settings.supabase_state_configured else ("local_directory" if settings.persistent_data_dir is not None else "project_filesystem"),
        "supabase_state": state_status,
        "auto_phase_workflows": settings.auto_phase_workflows,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/config")
def config() -> dict:
    return {
        "project": settings.app_name, "api_version": settings.api_version,
        "calculation_version": settings.calculation_version, "parameter_version": settings.parameter_version,
        "default_simulation_runs": settings.default_simulation_runs,
        "default_start_year": settings.default_start_year, "default_end_year": settings.default_end_year,
        "offline_mode": settings.offline_mode,
        "development_data_mode": True,
        "official_data_mode": True,
        "data_notice": "Official PSA provincial coconut-production data are used where available. Unavailable periods and future values are model-estimated and tagged in provenance.",
    }


@router.get("/sources")
def sources() -> dict:
    psa = official_metadata()
    return {"sources": [
        {"id": "psa-coconut-production", "name": "Philippine Statistics Authority Coconut Production", "type": "Official agricultural statistics", "enabled": True, "attribution": "Philippine Statistics Authority (PSA)", "coverage": psa.get("coverage"), "latest_update": psa.get("latest_update"), "table_code": psa.get("table_code"), "limitations": ["2026 contains preliminary Quarter 1 data; unavailable cells are model-estimated and tagged in provenance."]},
        {"id": "open-meteo", "name": "Open-Meteo", "type": "Deterministic short-term forecast", "enabled": not settings.offline_mode, "attribution": "Weather data by Open-Meteo.com and underlying agencies", "url": "https://open-meteo.com/", "limitations": ["Forecast fields are model output, not observations."]},
        {"id": "rainviewer", "name": "RainViewer", "type": "Radar observation", "enabled": not settings.offline_mode, "attribution": "RainViewer and original radar providers", "url": "https://www.rainviewer.com/", "limitations": ["Coverage and public tile availability vary by location."]},
        {"id": "nasa-gibs", "name": "NASA GIBS", "type": "Satellite observation imagery", "enabled": not settings.offline_mode, "attribution": "NASA EOSDIS GIBS", "url": "https://www.earthdata.nasa.gov/eosdis/science-system-description/eosdis-components/gibs"},
        {"id": "gdacs", "name": "GDACS", "type": "Supplemental tropical-cyclone information", "enabled": not settings.offline_mode, "attribution": "GDACS and contributing agencies", "url": "https://www.gdacs.org/", "limitations": ["Use PAGASA for official Philippine warnings."]},
        {"id": "pagasa", "name": "PAGASA", "type": "Official Philippine warning reference", "enabled": True, "attribution": "DOST-PAGASA", "url": "https://www.pagasa.dost.gov.ph/tropical-cyclone/severe-weather-bulletin"},
        {"id": "openstreetmap", "name": "OpenStreetMap", "type": "Basemap", "enabled": True, "attribution": "© OpenStreetMap contributors", "url": "https://www.openstreetmap.org/copyright"},
        {"id": "climate-demo", "name": "COCO-AID climate projection layer", "type": "Model-estimated long-term climate projection", "enabled": True, "attribution": "Scenario-based projection layer structured around CMIP6 periods and SSP conventions", "limitations": ["Future conditions are projections, not exact daily forecasts."]},
    ]}


@router.get("/official-data/summary")
def official_data_summary() -> dict:
    return official_metadata()


@router.get("/official-data/provinces")
def official_data_provinces() -> dict:
    return {"provinces": province_names(), "metadata": official_metadata()}


@router.get("/official-data/profile")
def official_data_profile(province: str = Query(default="South Cotabato", max_length=120), region: str | None = Query(default=None, max_length=120)) -> dict:
    return public_profile(province, region)


@router.get("/models")
def models() -> dict:
    return {"models": model_metadata()}


@router.get("/models/{model_name}")
def model(model_name: str) -> dict:
    result = model_metadata(model_name)
    if model_name not in result:
        raise HTTPException(404, "Model not found")
    return result[model_name]


@router.post("/farms", status_code=201)
def create_farm_route(farm: FarmCreate):
    return create_farm(farm)


@router.get("/farms")
def list_farms_route():
    return {"farms": list_farms()}


@router.get("/farms/{farm_id}")
def get_farm_route(farm_id: str):
    farm = get_farm(farm_id)
    if not farm:
        raise HTTPException(404, "Farm not found")
    return farm


@router.put("/farms/{farm_id}")
def update_farm_route(farm_id: str, farm: FarmPatch):
    result = update_farm(farm_id, farm)
    if not result:
        raise HTTPException(404, "Farm not found")
    return result


@router.delete("/farms/{farm_id}")
def delete_farm_route(farm_id: str):
    if not delete_farm(farm_id):
        raise HTTPException(404, "Farm not found")
    return {"deleted": True, "farm_id": farm_id}


@router.post("/weather/point")
async def weather_point(request: WeatherPointRequest):
    return await point_forecast(request)


@router.post("/weather/grid")
async def weather_grid_route(request: WeatherGridRequest):
    try:
        return await weather_grid(request)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/weather/frame")
async def weather_frame_route(request: WeatherFrameRequest):
    cube = await weather_grid(WeatherGridRequest(
        west=request.west, south=request.south, east=request.east, north=request.north,
        rows=request.rows, cols=request.cols, variables=request.variables,
        forecast_hours=384, model=request.model,
    ))
    index = min(request.hour_index, len(cube["times"]) - 1)
    matrices = {}
    for variable, point_series in cube["values"].items():
        flat = [series[index] if index < len(series) else None for series in point_series]
        matrices[variable] = [flat[row * request.cols:(row + 1) * request.cols] for row in range(request.rows)]
    return {
        "west": cube["west"], "south": cube["south"], "east": cube["east"], "north": cube["north"],
        "rows": request.rows, "cols": request.cols, "latitudes": cube["latitudes"], "longitudes": cube["longitudes"],
        "valid_time": cube["times"][index], "values": matrices,
        "elevation_m": cube.get("elevation_m"), "metadata": cube["metadata"],
    }


@router.post("/weather/cube")
async def weather_cube_route(request: WeatherCubeRequest):
    try:
        return await weather_cube(request)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


# Compatibility endpoints used by the embedded full Weather GIS viewer.
@router.get("/weather/point")
async def weather_point_get(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    model: str = Query(default="auto", max_length=80),
    forecast_days: int = Query(default=16, ge=1, le=16),
):
    return await point_forecast(WeatherPointRequest(
        latitude=latitude, longitude=longitude, model=model, forecast_days=forecast_days,
    ))


@router.get("/geocode/search")
async def weather_geocode_alias(q: str = Query(min_length=2, max_length=100), count: int = Query(default=6, ge=1, le=10)):
    return await geocode(q, count)


@router.get("/radar/frames")
async def radar_frames_alias():
    return await radar_frames()


@router.get("/storms/active")
async def storms_alias():
    return await active_storms()


@router.get("/warnings/philippines")
def warnings_alias():
    return weather_warnings()


@router.get("/weather/geocode")
async def weather_geocode(q: str = Query(min_length=2, max_length=100)):
    return await geocode(q)


@router.get("/weather/radar/frames")
async def weather_radar_frames():
    return await radar_frames()


@router.get("/weather/storms")
async def weather_storms():
    return await active_storms()


@router.get("/weather/warnings")
def weather_warnings():
    return {
        "source": "DOST-PAGASA", "source_type": "Official warning reference",
        "bulletin_url": "https://www.pagasa.dost.gov.ph/tropical-cyclone/severe-weather-bulletin",
        "message": "Use the official PAGASA bulletin for current Philippine tropical-cyclone warnings. COCO-AID does not invent warning polygons.",
    }


@router.post("/climate/projection")
def climate_projection_route(request: ClimateProjectionRequest):
    try:
        return climate_projection(request)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/climate/generate-trajectory")
def climate_trajectory_route(request: ClimateTrajectoryRequest):
    return generate_annual_trajectory(request)


@router.post("/farm-assessment")
def farm_assessment_route(farm: FarmCreate):
    return farm_assessment(farm)


@router.post("/pest-risk/evaluate")
def pest_risk_route(request: PestRiskRequest):
    return pest_assessment(request)


@router.post("/pest-risk/specific")
def pest_specific_route(request: PestSpecificRequest):
    return evaluate_specific_pests(request)


@router.post("/suitability/evaluate")
def suitability_route(request: SuitabilityRequest):
    return suitability_assessment(request)


@router.post("/simulation/run")
async def simulation_route(request: SimulationRequest):
    if request.runs > settings.max_simulation_runs:
        raise HTTPException(422, "Simulation count exceeds maximum")
    return await run_in_threadpool(run_simulation, request)


@router.post("/farm-site/forecast")
async def farm_site_forecast_route(request: FarmSiteForecastRequest):
    live_cube = None
    live_warning = None
    today = date.today()
    requested_start = request.start_date or date(request.start_year, 1, 1)
    provider_dates_can_overlap = (
        request.start_year <= today.year <= request.end_year
        and requested_start <= today + timedelta(days=10)
    )
    if request.include_live_short_term and not settings.offline_mode and provider_dates_can_overlap:
        bounds = farm_map_bounds(request.farm)
        try:
            live_cube = await asyncio.wait_for(weather_cube(WeatherCubeRequest(
                west=bounds["west"], south=bounds["south"],
                east=bounds["east"], north=bounds["north"],
                rows=6, cols=6, model="auto",
            )), timeout=min(8.0, settings.request_timeout_seconds))
        except TimeoutError:
            live_warning = "Short-term provider forecast timed out after 8 seconds; the long-term simulation continued without it."
        except (ProviderRateLimitError, ProviderUnavailableError, ValueError) as exc:
            live_warning = f"Short-term provider forecast could not be merged: {exc}"
    elif request.include_live_short_term and settings.offline_mode:
        live_warning = "Short-term provider forecast was not merged because COCO-AID is running offline."
    elif request.include_live_short_term and not provider_dates_can_overlap:
        live_warning = "Short-term provider data were not requested because the selected start date is outside the current numerical forecast window."
    return await run_in_threadpool(generate_farm_site_forecast, request, live_cube, live_warning)


@router.post("/scenarios/compare")
async def compare_route(request: ScenarioComparisonRequest):
    return await run_in_threadpool(compare_scenarios, request)


@router.post("/rehabilitation-map")
def rehab_map_route(farm: FarmCreate, rows: int = Query(default=5, ge=2, le=10), cols: int = Query(default=5, ge=2, le=10)):
    return rehabilitation_grid(farm, rows, cols)


@router.post("/rehabilitation-plan")
def rehab_plan_route(request: RehabilitationPlanRequest):
    return rehabilitation_event_plans(request)


@router.post("/analysis/full")
async def full_analysis_route(request: FullAnalysisRequest):
    return await run_in_threadpool(full_analysis, request)


@router.get("/analysis/{analysis_id}")
def get_analysis_route(analysis_id: str):
    analysis = get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(404, "Analysis not found")
    return analysis


@router.get("/database/summary")
def database_summary_route():
    return database_summary()


@router.get("/database/analyses")
def database_analyses_route(limit: int = Query(default=100, ge=1, le=500)):
    return {"analyses": list_analyses(limit)}


@router.delete("/database/analyses/{analysis_id}")
def database_delete_analysis_route(analysis_id: str):
    if not delete_analysis(analysis_id):
        raise HTTPException(404, "Analysis not found")
    return {"deleted": True, "analysis_id": analysis_id}


@router.get("/database/reports")
def database_reports_route(limit: int = Query(default=100, ge=1, le=500)):
    return {"reports": list_reports(limit)}


@router.post("/database/forecasts", status_code=201)
def database_save_forecast_route(request: ForecastSaveRequest):
    identifier = save_forecast(request.name, request.forecast, request.summary, request.farm_id, request.forecast_id)
    return {"forecast_id": identifier, "saved": True}


@router.get("/database/forecasts")
def database_forecasts_route(limit: int = Query(default=100, ge=1, le=500)):
    return {"forecasts": list_forecasts(limit)}


@router.get("/database/forecasts/{forecast_id}")
def database_forecast_route(forecast_id: str):
    record = get_forecast(forecast_id)
    if not record:
        raise HTTPException(404, "Forecast not found")
    return record


@router.delete("/database/forecasts/{forecast_id}")
def database_delete_forecast_route(forecast_id: str):
    if not delete_forecast(forecast_id):
        raise HTTPException(404, "Forecast not found")
    return {"deleted": True, "forecast_id": forecast_id}


@router.get("/assistant/status")
def assistant_status_route():
    return assistant_status()


@router.post("/assistant/configure")
def assistant_configure_route(request: AssistantKeyRequest):
    if not settings.allow_runtime_api_key_configuration:
        raise HTTPException(
            403,
            "Runtime API-key configuration is disabled for this deployment. Set GEMINI_API_KEY in the server environment instead.",
        )
    try:
        save_api_key(request.api_key)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return assistant_status()


@router.delete("/assistant/configure")
def assistant_clear_route():
    if not settings.allow_runtime_api_key_configuration:
        raise HTTPException(
            403,
            "Runtime API-key configuration is disabled for this deployment. Manage GEMINI_API_KEY in the server environment instead.",
        )
    clear_api_key()
    return assistant_status()


@router.post("/assistant/upload-document")
async def assistant_upload_document_route(file: UploadFile = File(...)):
    suffix = Path(file.filename or "document").suffix.lower()
    if suffix not in {".pdf", ".docx"}:
        raise HTTPException(422, "Only PDF and DOCX files are supported.")
    content = await file.read(15 * 1024 * 1024 + 1)
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(413, "Document exceeds the 15 MB local upload limit.")
    temp_dir = settings.cache_dir / "assistant_uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp = temp_dir / f"{datetime.now(UTC).timestamp():.0f}_{Path(file.filename or 'document').name}"
    temp.write_bytes(content)
    try:
        return await run_in_threadpool(store_uploaded_document, temp, Path(file.filename or "document").name)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    finally:
        temp.unlink(missing_ok=True)


@router.post("/assistant/attach-report/{report_id}")
async def assistant_attach_report_route(report_id: str):
    try:
        return await run_in_threadpool(attach_saved_report, report_id)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/assistant/chat")
async def assistant_chat_route(request: AssistantChatRequest):
    try:
        return await chat_with_gemini(
            request.message,
            [item.model_dump() for item in request.history],
            request.context,
            request.document_ids,
        )
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected CoCO-PILOT error")
        raise HTTPException(503, "CoCO-PILOT encountered a temporary service error. Check the API key and connection, then try again.") from exc


@router.post("/reports/generate")
async def generate_report_route(request: ReportRequest):
    analysis = request.analysis
    analysis_id = request.analysis_id
    if analysis_id:
        record = get_analysis(analysis_id)
        if not record:
            raise HTTPException(404, "Analysis not found")
        stored = deepcopy(record["result"])
        stored["metadata"] = record["metadata"]
        # A client may attach the latest weekly outlook to an existing full analysis.
        # Only known supplemental sections are merged; the stored analytical result
        # remains the source of truth for the core report.
        if isinstance(analysis, dict):
            for key in ("farm_site_forecast", "pest_specific", "farm_health_snapshot", "rehabilitation_event_plans", "report_notes"):
                if key in analysis:
                    stored[key] = analysis[key]
        analysis = stored
    generator = generate_docx if request.report_format == "docx" else generate_pdf
    report_id, path = await run_in_threadpool(generator, analysis, analysis_id)
    return {"report_id": report_id, "filename": path.name, "report_format": request.report_format, "download_url": f"/api/reports/{report_id}"}


@router.get("/reports/{report_id}")
def report_download(report_id: str):
    path = get_report(report_id)
    if not path or not path.exists():
        raise HTTPException(404, "Report not found")
    safe_root = settings.reports_dir.resolve()
    resolved = path.resolve()
    if safe_root not in resolved.parents:
        raise HTTPException(400, "Invalid report path")
    record = report_record(report_id) or {}
    report_type = record.get("report_type") or resolved.suffix.lstrip(".")
    media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if report_type == "docx" else "application/pdf"
    return FileResponse(resolved, media_type=media_type, filename=resolved.name)
