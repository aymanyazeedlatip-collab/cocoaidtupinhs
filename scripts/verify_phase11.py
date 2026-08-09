from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.coco_pilot.reports import FORMAL_REPORT_GENERATOR_VERSION
from app.interface.status import interface_status
from app.main import app



def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    required = [
        "app/static/phase11.css",
        "app/static/phase11.js",
        "app/static/weather-viewer/phase11.css",
        "app/static/weather-viewer/phase11.js",
        "app/interface/status.py",
        "manifests/phase11_interface_catalog.json",
        "manifests/phase11_asset_checksums.json",
        "manifests/phase11_audio_checksums.json",
        "manifests/phase11_endpoint_catalog.json",
        "tests/unit/test_phase11_interface.py",
        "tests/integration/test_phase11_api.py",
        "RELEASE_NOTES_PHASE_11.md",
    ]
    missing = [item for item in required if not (ROOT / item).is_file()]
    assert not missing, f"Missing Phase 11 files: {missing}"

    status = interface_status()
    assert status["version"] == "phase11-agritech-interface-1.3.23"
    assert status["theme"]["default"] == "official_white"
    assert status["theme"]["liquid_glass_enabled"] is False
    assert status["landing"]["interactive_coconut_hologram"] is True
    assert status["landing"]["full_3d_hologram"] is True
    assert status["landing"]["clean_landing_rehaul"] is True
    assert status["landing"]["entry_hologram_enabled"] is False
    assert status["landing"]["entry_background_carousel"] is True
    assert status["landing"]["entry_background_count"] == 7
    assert status["landing"]["entry_centered_orbits"] is True
    assert status["landing"]["home_fullscreen"] is True
    assert status["landing"]["home_hologram_only"] is True
    assert status["landing"]["farmer_step_guidance"] is True
    assert status["landing"]["full_bleed_farm_background"] is True
    assert status["landing"]["transparent_hologram_stage"] is True
    assert status["landing"]["parametric_coconut_mesh"] is True
    assert status["landing"]["annotation_free_hologram"] is True
    assert status["landing"]["white_orbit_rings"] is True
    assert status["landing"]["thick_white_orbit_rings"] is True
    assert status["landing"]["alternating_coconut_tree_mesh"] is True
    assert status["landing"]["smooth_mesh_transition"] is True
    assert status["accessibility"]["non_blocking_navigation"] is True
    assert status["accessibility"]["icon_only_navigation_state"] is True
    assert status["visualizations"]["chart_png_export"] is True
    assert status["audio"]["background_music_preserved"] is True
    assert FORMAL_REPORT_GENERATOR_VERSION == "formal-report-generator-1.1.0"

    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    for token in (
        "/static/phase11.css", "/static/phase11.js", "globalNavButton",
        "coconutHologramWorkspace", "holo-coconut-mesh", "Plant Sharper", "farmer-home-hero", "weather-gis-page", "Decision-support network",
        "Welcome to COCO-AID", "entry-background-carousel", "entry-center-orbit-d",
    ):
        assert token in html, f"Missing UI token: {token}"
    assert "Official PSA annual production" in html, "Official PSA baseline disclosure is missing"
    assert "Background music begins on this preview page" in html, "Preview audio disclosure is missing"

    css = (ROOT / "app/static/phase11.css").read_text(encoding="utf-8")
    assert "backdrop-filter: none !important" in css
    assert ".phase11-chart-tools" in css
    assert ".coconut-hologram" in css
    assert ".holo-coconut-3d" in css
    assert "coconutHologramPreview" not in html
    assert "entry-wordmark" not in html
    assert html.count("entry-background-slide") >= 7
    assert "entryCarouselFade" in css
    assert "Four steps from farm details to a clear action plan" in html
    assert 'id="navigationBackdrop"' not in html
    assert "/static/phase11.css?v=11.3.23" in html
    assert "/static/phase11.js?v=11.3.23" in html
    assert "const HOLD_MS = 5000" in (ROOT / "app/static/phase11.js").read_text(encoding="utf-8")
    assert "const TRANSITION_MS = 1250" in (ROOT / "app/static/phase11.js").read_text(encoding="utf-8")
    assert "border: 3px solid #ffffff !important" in css

    asset_manifest = json.loads((ROOT / "manifests/phase11_asset_checksums.json").read_text(encoding="utf-8"))
    for relative, expected in asset_manifest.items():
        assert _sha256(ROOT / relative) == expected, f"Phase 11 asset checksum mismatch: {relative}"
    audio_manifest = json.loads((ROOT / "manifests/phase11_audio_checksums.json").read_text(encoding="utf-8"))
    for relative, expected in audio_manifest.items():
        assert _sha256(ROOT / relative) == expected, f"Audio asset changed: {relative}"

    client = TestClient(app)
    response = client.get("/api/v2/interface/status")
    assert response.status_code == 200
    assert response.json()["availability"] == "available"
    assert client.get("/static/phase11.css").status_code == 200
    assert client.get("/static/phase11.js").status_code == 200
    assert client.get("/weather-viewer").status_code == 200

    print("PHASE 11 VERIFICATION PASSED")
    print(f"Interface version: {status['version']}")
    print(f"Report generator: {FORMAL_REPORT_GENERATOR_VERSION}")
    print(f"Preserved audio files: {len(audio_manifest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
