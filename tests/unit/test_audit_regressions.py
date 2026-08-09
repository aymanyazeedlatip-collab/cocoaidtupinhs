import asyncio
from pathlib import Path

from html.parser import HTMLParser

from app.climate.projections import climate_projection, year_climate_parameters
from app.gis.analysis import farm_assessment, rehabilitation_grid
from app.reports.pdf import generate_pdf
from app.schemas.analysis import ClimateProjectionRequest, ScenarioComparisonRequest
from app.schemas.farm import FarmCreate
from app.services.cache import TTLCache
from app.simulation.compare import compare_scenarios
from app.weather import providers
from app.schemas.weather import WeatherGridRequest


def test_climate_bounds_move_all_temperature_fields_and_sample_is_reproducible():
    lower = climate_projection(ClimateProjectionRequest(model_mode="lower"))
    upper = climate_projection(ClimateProjectionRequest(model_mode="upper"))
    sample_a = climate_projection(ClimateProjectionRequest(model_mode="sample"))
    sample_b = climate_projection(ClimateProjectionRequest(model_mode="sample"))
    for key in ("mean_temperature_c", "minimum_temperature_c", "maximum_temperature_c"):
        assert upper["monthly"][0][key] > lower["monthly"][0][key]
    assert sample_a == sample_b


def test_typhoon_proxy_is_not_artificially_changed_by_ssp():
    low = year_climate_parameters(2070, "ssp126", latitude=10)
    high = year_climate_parameters(2070, "ssp585", latitude=10)
    assert low["typhoon_probability"] == high["typhoon_probability"]


def test_far_climate_reference_is_disclosed():
    result = climate_projection(ClimateProjectionRequest(latitude=-30, longitude=-40))
    assert result["reference_distance_km"] > 250
    assert result["distance_warning"]


def test_scenario_response_is_compact_and_has_recommended_simulation():
    result = compare_scenarios(ScenarioComparisonRequest(runs=100, end_year=2030, seed=12))
    assert "recommended_simulation" in result
    assert all("simulation" not in item for item in result["ranking"])
    assert result["recommended_simulation"]["intervention"] == result["recommended_intervention"]


def test_farm_assessment_reports_area_and_yield_inconsistency():
    farm = FarmCreate()
    farm.location.polygon = [[6.0, 125.0], [6.0, 125.001], [6.001, 125.001], [6.001, 125.0]]
    farm.production.yield_tons_per_hectare = 12
    result = farm_assessment(farm)
    assert result["polygon_area_hectares"] is not None
    assert any("polygon area differs" in warning.lower() for warning in result["warnings"])
    assert any("does not match" in warning.lower() for warning in result["warnings"])


def test_rehabilitation_grid_does_not_invent_spatial_variation_and_excludes_outside_cells():
    farm = FarmCreate()
    farm.location.polygon = [[6.0, 125.0], [6.0, 125.02], [6.02, 125.0]]
    result = rehabilitation_grid(farm, rows=5, cols=5)
    assert result["excluded_cells_outside_polygon"] > 0
    assert result["spatial_resolution_status"] == "uniform_baseline"
    assert len({cell["priority"] for cell in result["cells"]}) == 1
    assert all(cell["spatial_evidence_status"] == "uniform_baseline" for cell in result["cells"])


class _NoDiskCache:
    def __init__(self):
        self.keys = []

    def get(self, key, max_age_seconds):
        self.keys.append(("get", key))
        return None

    def set(self, key, value):
        self.keys.append(("set", key))


def test_weather_grid_cache_key_includes_variables(monkeypatch):
    calls = []

    async def fake_get_json(url, params):
        calls.append(params["hourly"])
        variables = params["hourly"].split(",")
        payload = []
        for _ in range(9):
            hourly = {"time": ["2026-01-01T00:00", "2026-01-01T01:00"]}
            for variable in variables:
                hourly[variable] = [1.0, 2.0]
            payload.append({"hourly": hourly})
        return payload

    monkeypatch.setattr(providers, "cache", TTLCache())
    disk = _NoDiskCache()
    monkeypatch.setattr(providers, "persistent_cache", disk)
    monkeypatch.setattr(providers, "get_json", fake_get_json)
    monkeypatch.setattr(providers, "_provider_cooldown_until", 0.0)
    providers._grid_locks.clear()

    common = dict(west=124, south=6, east=125, north=7, rows=3, cols=3, forecast_hours=12)
    rain = asyncio.run(providers.weather_grid(WeatherGridRequest(**common, variables=["precipitation"])))
    cloud = asyncio.run(providers.weather_grid(WeatherGridRequest(**common, variables=["cloud_cover"])))
    assert calls == ["precipitation", "cloud_cover"]
    assert set(rain["values"]) == {"precipitation"}
    assert set(cloud["values"]) == {"cloud_cover"}


def test_pdf_handles_markup_in_user_values(tmp_path, monkeypatch):
    from app.reports import pdf as pdf_module
    monkeypatch.setattr(pdf_module.settings, "reports_dir", tmp_path)
    analysis = {
        "overview": {"farm_name": "A&B <Farm>", "recommended_intervention": "combined_rehabilitation"},
        "farm_assessment": {"warnings": ["Verify <area> & yield"]},
        "scientific_warning": "Synthetic <development> & validation warning.",
        "scenario_comparison": {"ranking": [], "recommended_intervention": "monitoring"},
        "recommended_simulation": {"summary": {}, "yearly": []},
        "metadata": {"limitations": ["No real-world validation"]},
    }
    _, path = generate_pdf(analysis)
    assert path.exists() and path.stat().st_size > 1000
    assert path.read_bytes().startswith(b"%PDF")


def test_frontend_uses_backend_results_and_has_required_workflow_sections():
    root = Path(__file__).resolve().parents[2]
    html_text = (root / "app/static/index.html").read_text(encoding="utf-8")
    js_text = (root / "app/static/app.js").read_text(encoding="utf-8")
    assert "renderOverviewChart({yearly" not in js_text
    assert "/api/farm-site/forecast" in js_text
    assert "/api/official-data/profile" in js_text
    for section in ("landing", "farm-setup", "outlook", "extreme-weather", "health", "reports", "database"):
        assert f'id="{section}"' in html_text
    assert "Official PSA annual production" in html_text
    assert "estimated 2026" in html_text.lower()


def test_polygon_rejects_one_or_two_vertices():
    import pytest
    from app.schemas.farm import FarmLocation
    with pytest.raises(Exception):
        FarmLocation(polygon=[[6.0, 125.0], [6.1, 125.1]])


def test_polygonless_rehabilitation_bounds_approximately_match_entered_area():
    from app.gis.analysis import polygon_area_hectares
    farm = FarmCreate(area_hectares=5)
    farm.location.polygon = []
    result = rehabilitation_grid(farm, rows=3, cols=3)
    b = result['bounds']
    rectangle = [[b['south'], b['west']], [b['south'], b['east']], [b['north'], b['east']], [b['north'], b['west']]]
    estimated = polygon_area_hectares(rectangle)
    assert 4.5 <= estimated <= 5.5


def test_weather_integrated_frontend_has_unique_and_resolved_ids():
    import re
    root = Path(__file__).resolve().parents[2]
    html_text = (root / 'app/static/index.html').read_text(encoding='utf-8')
    js_text = (root / 'app/static/app.js').read_text(encoding='utf-8')

    class AllIdParser(HTMLParser):
        def __init__(self):
            super().__init__(); self.ids = []
        def handle_starttag(self, tag, attrs):
            value = dict(attrs).get('id')
            if value: self.ids.append(value)

    parser = AllIdParser(); parser.feed(html_text)
    assert len(parser.ids) == len(set(parser.ids))
    used_ids = set(re.findall(r"\$\([\'\"]([^\'\"]+)[\'\"]\)", js_text))
    assert not (used_ids - set(parser.ids))
    for required in ('landingMap', 'farmMap', 'forecastMap', 'forecastSlider',
                     'weatherViewerFrame', 'productionChart', 'hazardTimeline',
                     'rehabMap', 'settingsDrawer', 'database'):
        assert required in parser.ids
    assert 'timelineMarker' in js_text
    assert 'chartjs-plugin-zoom' in html_text

