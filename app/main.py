from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
import logging
import threading
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware

from app.api.routes import router as legacy_router
from app.api.v2.routes import router as v2_router
from app.core.config import settings
from app.core.error_handlers import install_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.data_foundation.seeding import seed_reference_data
from app.models.registry import preload_models
from app.services.supabase_state import supabase_state
from app.storage.database import initialize_database
from app.workflows.auto_phase_runner import kick as kick_auto_phase_workflow

configure_logging()
preload_models()
ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"
logger = logging.getLogger(__name__)


def _automatic_workflow_loop() -> None:
    """Server-side fallback that keeps Phase 9/10 automatic in deployed environments."""
    time.sleep(10.0)
    base_url = f"http://127.0.0.1:{settings.port}"
    while True:
        try:
            kick_auto_phase_workflow(base_url)
        except Exception as exc:  # pragma: no cover - deployment resilience path
            logger.warning("Automatic Phase 9/10 deployment check skipped: %s", exc)
        time.sleep(float(settings.auto_phase_poll_seconds))



@asynccontextmanager
async def lifespan(_: FastAPI):
    # Render Free has an ephemeral filesystem. When Supabase state sync is enabled,
    # restore the latest private SQLite snapshot before migrations and seeding.
    supabase_state.validate_configuration()
    if supabase_state.configured:
        supabase_state.ensure_bucket()
        supabase_state.restore_database()

    initialize_database()
    if settings.auto_seed_reference_data:
        seed_reference_data()
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    settings.private_settings_path.parent.mkdir(parents=True, exist_ok=True)

    if supabase_state.configured:
        # First deployment has no remote snapshot. Migrations + reference seeding
        # create it automatically, so no SQL setup or manual IDs are required.
        supabase_state.sync_database(force=True)
        supabase_state.start_background_sync()

    if settings.auto_phase_workflows:
        threading.Thread(
            target=_automatic_workflow_loop,
            daemon=True,
            name="cocoaid-deployment-auto-phase9-10",
        ).start()
    try:
        yield
    finally:
        supabase_state.stop_background_sync()


app = FastAPI(
    title=settings.app_name,
    version=settings.api_version,
    description="Bayesian and geospatial coconut rehabilitation decision-support research prototype.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=5)
app.add_middleware(RequestContextMiddleware)
install_exception_handlers(app)

if settings.enable_legacy_api:
    app.include_router(legacy_router)
if settings.enable_v2_contract_api:
    app.include_router(v2_router)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/weather-viewer", include_in_schema=False)
def weather_viewer():
    return FileResponse(STATIC / "weather-viewer" / "index.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(STATIC / "assets" / "brand" / "coco-aid-favicon.png", media_type="image/png")


@app.get("/{path:path}", include_in_schema=False)
def static_fallback(path: str):
    if path.startswith("api/"):
        from app.core.errors import CocoAidError

        raise CocoAidError("API endpoint not found", status_code=404, details={"path": f"/{path}"})
    static_root = STATIC.resolve()
    candidate = (STATIC / path).resolve()
    if candidate != static_root and static_root in candidate.parents and candidate.exists() and candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(STATIC / "index.html")
