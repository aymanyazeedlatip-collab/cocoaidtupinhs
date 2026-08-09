from __future__ import annotations

from app.data_foundation import repository
from app.data_foundation.seeding import seed_reference_data


def test_intercrop_income_assessment_is_sanitized_and_seeded_as_aggregates():
    counts = seed_reference_data()
    assert counts["source_documents"] == 16
    assert counts["intercrop_economic_profiles"] == 3
    assessment = repository.intercrop_income_assessment()
    assert assessment["intercrop_record_count"] == 127
    assert set(assessment["crop_profiles"]) == {"cacao", "coffee"}
    assert assessment["crop_profiles"]["cacao"]["record_count"] == 59
    assert assessment["crop_profiles"]["coffee"]["record_count"] == 68
    assert len(assessment["site_profiles"]) == 3
    assert assessment["privacy"]["farmer_names_exposed"] is False
    assert assessment["privacy"]["row_level_records_exposed"] is False
    assert all("farmer" not in key.lower() for profile in assessment["site_profiles"] for key in profile)
    assert any("net profit" in item.lower() for item in assessment["prohibited_or_deferred_uses"])
