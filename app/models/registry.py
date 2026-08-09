from __future__ import annotations

import hashlib
import json
import logging
import warnings
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
from typing import Any, Iterable

import joblib
import pandas as pd

from app.core.config import settings

logger = logging.getLogger(__name__)

MODEL_FILES = {
    "production": "production_model.joblib",
    "pest": "pest_model.joblib",
    "suitability": "suitability_model.joblib",
}
MODEL_SERIALIZATION_RUNTIME = {
    "scikit-learn": "1.9.0",
    "joblib": None,
}


def _installed_version(package: str) -> str | None:
    try:
        return package_version(package)
    except PackageNotFoundError:
        return None


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def model_runtime_status() -> dict[str, Any]:
    expected = MODEL_SERIALIZATION_RUNTIME["scikit-learn"]
    installed = _installed_version("scikit-learn")
    compatible = installed == expected
    return {
        "expected_scikit_learn": expected,
        "installed_scikit_learn": installed,
        "compatible": compatible,
        "strict_mode": settings.strict_model_runtime_compatibility,
        "mode": "exact" if compatible else "legacy_compatibility",
        "action": None if compatible else f"Install scikit-learn=={expected} for exact artifact reproducibility.",
    }


@lru_cache(maxsize=3)
def load_model(name: str) -> dict[str, Any] | None:
    filename = MODEL_FILES.get(name)
    if not filename:
        return None
    path = settings.artifacts_dir / filename
    if not path.exists():
        return None

    runtime = model_runtime_status()
    if settings.strict_model_runtime_compatibility and not runtime["compatible"]:
        logger.error(
            "Refusing to load %s model: scikit-learn runtime %s does not match artifact runtime %s",
            name,
            runtime["installed_scikit_learn"],
            runtime["expected_scikit_learn"],
        )
        return None

    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            artifact = joblib.load(path)
        version_warnings = [str(item.message) for item in caught if "InconsistentVersionWarning" in item.category.__name__]
        if version_warnings:
            logger.warning(
                "Loaded %s model in compatibility mode; exact serialized runtime is not active. Status: %s",
                name,
                runtime,
            )
    except Exception as exc:  # artifact may be incompatible with the installed sklearn version
        logger.warning("Could not load model artifact %s: %s", name, exc)
        return None
    if not isinstance(artifact, dict) or "pipeline" not in artifact or "features" not in artifact:
        logger.warning("Model artifact %s has an invalid structure", name)
        return None
    return artifact


def clear_model_cache() -> None:
    load_model.cache_clear()


def predict_many(name: str, rows: Iterable[dict[str, Any]]) -> list[float | None]:
    rows = list(rows)
    if not rows:
        return []
    artifact = load_model(name)
    if artifact is None:
        return [None] * len(rows)
    features = artifact["features"]
    frame = pd.DataFrame([{feature: row.get(feature) for feature in features} for row in rows])
    pipeline = artifact["pipeline"]
    try:
        if name == "pest":
            values = pipeline.predict_proba(frame)[:, 1]
        else:
            values = pipeline.predict(frame)
    except Exception as exc:
        logger.warning("Model prediction failed for %s: %s", name, exc)
        return [None] * len(rows)
    return [float(value) for value in values]


def predict(name: str, row: dict[str, Any]) -> float | None:
    return predict_many(name, [row])[0]


def model_metadata(name: str | None = None) -> dict[str, Any]:
    if name is not None and name not in MODEL_FILES:
        return {}
    names = [name] if name else list(MODEL_FILES)
    result: dict[str, Any] = {}
    runtime = model_runtime_status()
    for item in names:
        artifact = load_model(item)
        filename = MODEL_FILES[item]
        artifact_path = settings.artifacts_dir / filename
        card_path = settings.model_cards_dir / f"{item.upper()}_MODEL_CARD.json"
        try:
            card = json.loads(card_path.read_text(encoding="utf-8")) if card_path.exists() else {}
        except (OSError, ValueError, json.JSONDecodeError):
            card = {}
        result[item] = {
            "available": artifact is not None,
            "version": artifact.get("version") if artifact else "formula-fallback-1.0",
            "features": artifact.get("features", []) if artifact else [],
            "card": card,
            "fallback_active": artifact is None,
            "artifact": {
                "filename": filename,
                "sha256": _sha256(artifact_path),
                "serialized_runtime": MODEL_SERIALIZATION_RUNTIME,
            },
            "runtime_compatibility": runtime,
        }
    return result


def preload_models() -> None:
    """Load development artifacts before request worker threads use them."""
    for model_name in MODEL_FILES:
        load_model(model_name)
