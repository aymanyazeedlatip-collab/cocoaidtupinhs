from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.coco_pilot.reports import FORMAL_REPORT_GENERATOR_VERSION
from app.interface.status import interface_status

MANIFESTS = ROOT / "manifests"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(name: str, payload) -> None:
    MANIFESTS.mkdir(parents=True, exist_ok=True)
    (MANIFESTS / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    assets = [
        "app/static/index.html",
        "app/static/styles.css",
        "app/static/app.js",
        "app/static/phase11.css",
        "app/static/phase11.js",
        "app/static/weather-viewer/index.html",
        "app/static/weather-viewer/styles.css",
        "app/static/weather-viewer/app.js",
        "app/static/weather-viewer/phase11.css",
        "app/static/weather-viewer/phase11.js",
    ]
    _write("phase11_interface_catalog.json", {
        **interface_status(),
        "formal_report_generator_version": FORMAL_REPORT_GENERATOR_VERSION,
        "static_assets": assets,
    })
    _write("phase11_asset_checksums.json", {relative: _sha256(ROOT / relative) for relative in assets})
    _write("phase11_endpoint_catalog.json", {
        "interface_status": "/api/v2/interface/status",
        "main_interface": "/",
        "weather_interface": "/weather-viewer",
        "decision_support": "/api/v2/decision-support/status",
        "formal_reports": "/api/v2/formal-reports",
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
