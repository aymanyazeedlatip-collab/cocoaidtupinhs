from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REQUIRED = [
    "PROJECT_INITIATION.md",
    "DEVELOPMENT_STATUS.md",
    "docs/COCOAID_REHAUL_VISION.md",
    "docs/phase_0/SYSTEM_INVENTORY.md",
    "docs/phase_0/API_INVENTORY.md",
    "docs/phase_0/MODEL_INVENTORY.md",
    "docs/phase_0/DATABASE_INVENTORY.md",
    "docs/phase_0/DATA_SOURCE_INVENTORY.md",
    "docs/phase_0/KNOWN_ISSUES.md",
    "docs/phase_0/MIGRATION_MAP.md",
    "docs/phase_0/SECURITY_AND_PRIVACY.md",
    "manifests/legacy_baseline_manifest.json",
    "manifests/model_checksums.json",
    "manifests/input_archive_checksums.json",
    "manifests/farmer_workbook_audit.json",
    "baseline_snapshots/test_results.txt",
    "baseline_snapshots/reference_outputs/index.json",
    "tests/fixtures/reference_farms/small_low_risk.json",
    "tests/fixtures/reference_farms/medium_baseline.json",
    "tests/fixtures/reference_farms/large_high_risk.json",
]


def fail(message: str) -> None:
    raise SystemExit(f"PHASE 0 VERIFICATION FAILED: {message}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(*args: str, binary: bool = False):
    result = subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=not binary)
    return result.stdout


def main() -> None:
    for relative in REQUIRED:
        if not (ROOT / relative).exists():
            fail(f"missing required artifact: {relative}")

    tags = git("tag", "--list").splitlines()
    if "v2.11-legacy-baseline" not in tags:
        fail("legacy baseline tag is missing")

    branch = git("branch", "--show-current").strip()
    if branch != "develop":
        fail(f"expected develop branch, found {branch!r}")

    baseline = json.loads((ROOT / "manifests/legacy_baseline_manifest.json").read_text(encoding="utf-8"))
    if baseline.get("baseline_tag") != "v2.11-legacy-baseline":
        fail("baseline manifest points to an unexpected tag")
    for item in baseline["files"]:
        content = git("show", f"v2.11-legacy-baseline:{item['path']}", binary=True)
        if len(content) != item["size_bytes"]:
            fail(f"baseline size mismatch: {item['path']}")
        if hashlib.sha256(content).hexdigest() != item["sha256"]:
            fail(f"baseline hash mismatch: {item['path']}")

    model_checksums = json.loads((ROOT / "manifests/model_checksums.json").read_text(encoding="utf-8"))
    for name, item in model_checksums.items():
        path = ROOT / item["path"]
        if not path.exists() or sha256(path) != item["sha256"]:
            fail(f"model checksum mismatch for {name}")

    raw_checksums_path = ROOT / "manifests/raw_source_checksums.json"
    if raw_checksums_path.exists():
        for item in json.loads(raw_checksums_path.read_text(encoding="utf-8")):
            path = ROOT / item["path"]
            if path.exists() and sha256(path) != item["sha256"]:
                fail(f"raw source checksum mismatch: {item['path']}")

    from app.schemas.farm import FarmCreate

    for fixture in sorted((ROOT / "tests" / "fixtures" / "reference_farms").glob("*.json")):
        FarmCreate.model_validate(json.loads(fixture.read_text(encoding="utf-8")))

    index = json.loads((ROOT / "baseline_snapshots" / "reference_outputs" / "index.json").read_text(encoding="utf-8"))
    if len(index) != 3:
        fail(f"expected 3 reference outputs, found {len(index)}")
    for item in index:
        if not (ROOT / "baseline_snapshots" / "reference_outputs" / item["output"]).exists():
            fail(f"missing reference output: {item['output']}")

    test_text = (ROOT / "baseline_snapshots" / "test_results.txt").read_text(encoding="utf-8")
    if "111 passed" not in test_text:
        fail("baseline regression result does not contain '111 passed'")

    forbidden = [ROOT / ".env", ROOT / "data" / "private_settings.json"]
    for path in forbidden:
        if path.exists():
            fail(f"secret-bearing runtime file is present: {path.relative_to(ROOT)}")

    audit = json.loads((ROOT / "manifests" / "farmer_workbook_audit.json").read_text(encoding="utf-8"))
    if audit.get("total_records") != 17798 or audit.get("sheet_count") != 12:
        fail("farmer workbook structure does not match the recorded source")

    print("COCOAID Phase 0 verification passed.")
    print(f"Baseline files verified: {baseline['file_count']}")
    print(f"Model artifacts verified: {len(model_checksums)}")
    print(f"Reference farms verified: {len(index)}")
    print("Regression baseline: 111 passed")


if __name__ == "__main__":
    main()
