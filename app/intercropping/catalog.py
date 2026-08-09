from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REQUIREMENT_PATH = ROOT / "data" / "reference" / "intercrop_requirement_profiles.json"


def load_requirement_catalog() -> dict[str, Any]:
    return json.loads(REQUIREMENT_PATH.read_text(encoding="utf-8"))


def requirement_profiles() -> dict[str, dict[str, Any]]:
    catalog = load_requirement_catalog()
    return {item["candidate_id"]: item for item in catalog["profiles"]}
