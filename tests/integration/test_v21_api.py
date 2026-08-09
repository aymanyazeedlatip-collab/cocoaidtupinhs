from __future__ import annotations

import io
import zipfile
from datetime import date

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.farm import FarmCreate

client = TestClient(app)


def test_pest_specific_endpoint_returns_flash_card_contract():
    farm = FarmCreate()
    farm.symptoms.visible_scale_insects = True
    farm.symptoms.yellowing = True
    response = client.post("/api/pest-risk/specific", json={
        "farm": farm.model_dump(mode="json"),
        "temperature_c": 28,
        "humidity_percent": 86,
        "rainfall_mm_week": 55,
        "wind_speed_kmh": 12,
        "farm_condition_score": .55,
    })
    assert response.status_code == 200
    data = response.json()
    assert len(data["pests"]) >= 8
    assert all(0 <= row["outbreak_score"] <= 100 for row in data["pests"])
    assert all(row["image_url"].startswith(("/static/assets/pests/", "https://")) for row in data["pests"])
    assert all(row["ai_recommendations"] for row in data["pests"])


def test_frontend_contains_smooth_heatmap_health_donuts_and_hazard_dates():
    html = client.get("/").text
    javascript = client.get("/static/app.js").text
    assert 'id="healthPestDonut"' in html
    assert 'id="healthSuitabilityDonut"' in html
    assert 'id="healthConditionDonut"' in html
    assert 'id="pestCardDeck"' in html
    assert 'id="hazardDateRail"' in html
    assert "bilinearGridValue" in javascript
    assert 'filter = "blur(3.5px) saturate(1.12)"' in javascript
    assert 'await runHealth({ silent: true, keepOverlay: true })' in javascript


def test_rich_pdf_and_docx_reports_include_new_sections_and_valid_assets():
    farm = FarmCreate()
    analysis = client.post("/api/analysis/full", json={
        "farm": farm.model_dump(mode="json"), "runs": 100, "end_year": 2030,
    }).json()
    forecast = client.post("/api/farm-site/forecast", json={
        "farm": farm.model_dump(mode="json"),
        "start_year": 2026, "end_year": 2027, "start_date": "2026-07-19",
        "runs": 100, "include_live_short_term": False,
    }).json()
    frame = max(forecast["frames"], key=lambda item: item.get("event_severity", 0))
    forecast["critical_weather_frames"] = [frame]
    specific = client.post("/api/pest-risk/specific", json={
        "farm": farm.model_dump(mode="json"),
        "temperature_c": frame["temperature_c"],
        "humidity_percent": frame["humidity_percent"],
        "rainfall_mm_week": frame["rainfall_mm"],
        "wind_speed_kmh": frame["wind_speed_kmh"],
        "farm_condition_score": frame["farm_condition_score"],
    }).json()
    supplement = {
        "farm_site_forecast": forecast,
        "pest_specific": specific,
        "farm_health_snapshot": {
            "farm_condition_score": frame["farm_condition_score"],
            "rehabilitation_summary": {"high_priority_cells": 0},
        },
    }
    for report_format in ("pdf", "docx"):
        generated = client.post("/api/reports/generate", json={
            "analysis_id": analysis["analysis_id"],
            "analysis": supplement,
            "report_format": report_format,
        })
        assert generated.status_code == 200
        downloaded = client.get(generated.json()["download_url"])
        assert downloaded.status_code == 200
        assert len(downloaded.content) > 20_000
        if report_format == "pdf":
            assert downloaded.content.startswith(b"%PDF")
        else:
            assert downloaded.content.startswith(b"PK")
            with zipfile.ZipFile(io.BytesIO(downloaded.content)) as archive:
                document_xml = archive.read("word/document.xml").decode("utf-8")
                styles_xml = archive.read("word/styles.xml").decode("utf-8")
                assert "Critical Weather Dates" in document_xml
                assert "Pest-Specific Risk Assessment" in document_xml
                assert "Times New Roman" in styles_xml
                assert any(name.startswith("word/media/") for name in archive.namelist())
