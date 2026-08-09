from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.data_foundation.seeding import seed_reference_data
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def _seed():
    seed_reference_data(database_path=settings.database_path)


def test_phase2_summary_and_public_reference_endpoints(client):
    _seed()
    summary = client.get("/api/v2/data-foundation/summary")
    assert summary.status_code == 200
    body = summary.json()
    assert body["catalog_version"] == "phase4-pca-and-economic-reference-1"
    assert body["counts"]["coconut_varieties"] == 30
    assert body["counts"]["variety_parameters"] == 408
    assert body["privacy"]["farmer_names_exposed"] is False

    sources = client.get("/api/v2/data-foundation/source-documents").json()["documents"]
    assert len(sources) == 14
    assert all(item["access_class"] != "restricted_pii" for item in sources)

    assert len(client.get("/api/v2/data-foundation/varieties?variety_class=tall").json()["varieties"]) == 12
    assert len(client.get("/api/v2/data-foundation/varieties?variety_class=dwarf").json()["varieties"]) == 12
    assert len(client.get("/api/v2/data-foundation/varieties?variety_class=hybrid").json()["varieties"]) == 6
    assert len(client.get("/api/v2/data-foundation/pests").json()["pests"]) == 5
    assert len(client.get("/api/v2/data-foundation/intercrops").json()["candidates"]) == 35
    assert len(client.get("/api/v2/data-foundation/canopy-light?age_years=20").json()["parameters"]) > 0
    assert len(client.get("/api/v2/data-foundation/fertilization-scenarios").json()["scenarios"]) == 2


def test_phase2_validation_privacy_and_openapi_contract(client):
    _seed()
    invalid = client.get("/api/v2/data-foundation/canopy-light?age_years=30")
    assert invalid.status_code == 422
    assert "20- and 40-year-old" in invalid.json()["detail"]
    registry = client.get("/api/v2/data-foundation/farmer-registry-summary")
    assert registry.status_code == 200
    lowered = str(registry.json()).lower()
    assert "last_name" not in lowered and "first_name" not in lowered
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v2/data-foundation/summary" in paths
    assert "/api/v2/data-foundation/varieties" in paths
