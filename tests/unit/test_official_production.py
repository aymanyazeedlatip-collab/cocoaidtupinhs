from __future__ import annotations

from app.data.official_production import metadata, province_names, public_profile, production_calibration


def test_psa_metadata_and_province_catalog_are_available():
    info = metadata()
    assert info["source"] == "Philippine Statistics Authority (PSA)"
    assert info["table_code"] == "2E4EVCP1"
    assert info["unit"] == "metric tons"
    assert info["coverage"] == "2010-2026"
    provinces = province_names()
    assert len(provinces) >= 80
    assert any(item["province"] == "South Cotabato" for item in provinces)


def test_south_cotabato_has_three_product_history_and_provenance():
    profile = public_profile("South Cotabato")
    assert profile["reference_level"] == "province"
    for product in ("coconut_w_husk", "coconut_mature", "coconut_young"):
        history = profile["products"][product]["history"]
        assert [row["year"] for row in history] == list(range(2010, 2027))
        assert next(row for row in history if row["year"] == 2025)["status"] == "official_psa"
        assert next(row for row in history if row["year"] == 2026)["status"].startswith("estimated")
        assert profile["products"][product]["latest_official_2025_tons"] > 0


def test_mature_and_young_conserve_with_husk_reference():
    profile = public_profile("South Cotabato")
    products = profile["products"]
    husk = products["coconut_w_husk"]["latest_official_2025_tons"]
    mature = products["coconut_mature"]["latest_official_2025_tons"]
    young = products["coconut_young"]["latest_official_2025_tons"]
    assert abs((mature + young) - husk) < 0.05
    calibration = production_calibration("South Cotabato")
    assert abs(calibration["mature_share"] + calibration["young_share"] - 1) < 1e-9


def test_unknown_province_falls_back_without_claiming_province_data():
    profile = public_profile("Not A Province", "REGION XII (SOCCSKSARGEN)")
    assert profile["reference_level"] in {"region", "national"}
    assert profile["metadata"]["source"] == "Philippine Statistics Authority (PSA)"
