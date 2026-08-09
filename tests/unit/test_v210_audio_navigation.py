from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app" / "static" / "styles.css").read_text(encoding="utf-8")


def test_v210_version_and_light_preview_contract():
    client = TestClient(app)
    assert client.get("/api/health").json()["api_version"] == "2.11.0"
    assert 'id="experiencePreview"' in HTML
    assert 'id="previewAudioHint"' in HTML
    assert "Background music begins on this preview page" in HTML
    assert "rgba(250, 255, 251, .92)" in CSS
    assert "rgba(255,255,255,.88)" in CSS


def test_music_starts_on_preview_at_constant_ten_percent():
    assert 'id="backgroundMusic"' in HTML
    assert "autoplay" in HTML
    assert "const previewMusicStarted = await startBackgroundMusic();" in JS
    assert "function effectiveBgmVolume()" in JS
    assert "return 0.10;" in JS
    assert 'id="bgmVolumeOutput">10%</output>' in HTML
    assert 'id="bgmVolumeSetting"' not in HTML
    assert "state.bgmDucked" not in JS


def test_sidebar_collapse_and_brand_cleanup_contract():
    assert 'id="sidebarCollapseButton"' in HTML
    assert 'class="nav-label">Home</span>' in HTML
    assert '<small>Cocon</small>' not in HTML
    assert "sidebarCollapsed" in JS
    assert "function applySidebarState()" in JS
    assert "body.sidebar-collapsed" in CSS
    assert "--sidebar: 82px" in CSS


def test_settings_voice_removed_and_drawer_scroll_is_contained():
    assert 'settings: "/static/assets/audio/settings.mp3"' not in JS
    assert 'playVoiceLine("settings")' not in JS
    assert not (ROOT / "app" / "static" / "assets" / "audio" / "settings.mp3").exists()
    assert "overflow-y: auto" in CSS
    assert "overscroll-behavior: contain" in CSS
    assert '$("settingsDrawer")?.addEventListener("wheel"' in JS


def test_remaining_audio_assets_are_bundled_and_served():
    client = TestClient(app)
    filenames = [
        "bgm-1.mp3",
        "home.mp3",
        "farm-setup.mp3",
        "farm-site-forecast.mp3",
        "extreme-weather.mp3",
        "farm-health.mp3",
        "reports.mp3",
        "database.mp3",
        "about.mp3",
        "weather-gis.mp3",
        "forecast-complete.mp3",
    ]
    for filename in filenames:
        path = ROOT / "app" / "static" / "assets" / "audio" / filename
        assert path.exists()
        assert path.stat().st_size > 10_000
        response = client.get(f"/static/assets/audio/{filename}")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("audio/")
        assert len(response.content) == path.stat().st_size
