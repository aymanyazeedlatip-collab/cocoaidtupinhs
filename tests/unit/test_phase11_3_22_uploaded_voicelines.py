from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[2]
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
STATUS = (ROOT / "app/interface/status.py").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")

def test_phase_version_and_cache_are_current():
    assert "phase11-agritech-interface-1.3.23" in STATUS
    for asset in ("styles.css", "phase11.css", "app.js", "phase11.js"):
        assert f"/static/{asset}?v=11.3.23" in HTML

def test_every_user_facing_tab_has_its_uploaded_voice_asset():
    expected = {
        "landing": "home.mp3", "farm-setup": "farm-setup.mp3",
        "outlook": "farm-site-forecast.mp3", "extreme-weather": "extreme-weather.mp3",
        "intercropping": "intercropping.mp3", "health": "farm-health.mp3",
        "pest-risk": "pest-risk.mp3", "intelligence": "decision-support.mp3",
        "database": "database.mp3", "reports": "reports.mp3",
        "about": "about.mp3", "weather-gis-page": "weather-gis.mp3",
    }
    for key, filename in expected.items():
        assert filename in JS, (key, filename)
        assert (ROOT / "app/static/assets/audio" / filename).is_file()

def test_bgm_and_forecast_complete_cue_remain_present():
    assert (ROOT / "app/static/assets/audio/bgm-1.mp3").is_file()
    assert (ROOT / "app/static/assets/audio/forecast-complete.mp3").is_file()
