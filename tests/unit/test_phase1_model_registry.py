from __future__ import annotations

from pathlib import Path

from app.models.registry import model_metadata, model_runtime_status


def test_model_registry_exposes_hash_feature_schema_and_runtime_status():
    metadata = model_metadata()
    assert set(metadata) == {"production", "pest", "suitability"}
    for model in metadata.values():
        assert model["available"] is True
        assert len(model["artifact"]["sha256"]) == 64
        assert model["features"]
        assert model["runtime_compatibility"]["expected_scikit_learn"] == "1.9.0"


def test_requirements_pin_exact_serialization_runtime():
    requirements = Path("requirements.txt").read_text(encoding="utf-8")
    assert "scikit-learn==1.9.0" in requirements
    status = model_runtime_status()
    assert status["mode"] in {"exact", "legacy_compatibility"}
