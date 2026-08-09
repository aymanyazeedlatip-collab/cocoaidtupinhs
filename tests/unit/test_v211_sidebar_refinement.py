from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[2]
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")


def test_v211_version():
    assert TestClient(app).get("/api/health").json()["api_version"] == "2.11.0"


def test_expanded_nav_labels_use_available_width():
    assert ".nav-item .nav-label" in CSS
    assert "flex: 1 1 auto" in CSS
    assert "max-width: 176px" in CSS
    assert "body:not(.sidebar-collapsed) .nav-item .nav-label" in CSS
    assert ".nav-item .nav-icon" in CSS


def test_sidebar_has_smooth_transition_and_arrow_motion():
    assert "--sidebar-motion: 380ms" in CSS
    assert "transition: grid-template-columns var(--sidebar-motion)" in CSS
    assert "transition:" in CSS and "width var(--sidebar-motion)" in CSS
    assert "sidebar-collapse-arrow" in HTML
    assert "body.sidebar-collapsed .sidebar-collapse-arrow" in CSS
    assert "sidebar-transitioning" in JS


def test_background_refits_and_maps_resize_after_sidebar_transition():
    assert "center center / cover no-repeat" in CSS
    assert "body.sidebar-transitioning .landing-page::before" in CSS
    assert 'window.dispatchEvent(new Event("resize"))' in JS
    assert "map?.invalidateSize?.()" in JS
