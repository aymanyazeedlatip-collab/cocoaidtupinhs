from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data_foundation.repository import summary
from app.data_foundation.seeding import REFERENCE_CATALOG, SOURCE_CATALOG, seed_reference_data
from app.storage.migrations import MIGRATIONS, MigrationManager


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    destination = ROOT / "manifests"
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cocoaid-manifest-") as temporary:
        database = Path(temporary) / "phase2.sqlite3"
        MigrationManager(database).upgrade()
        seed_reference_data(database_path=database)
        counts = summary(database_path=database)
    source = json.loads(SOURCE_CATALOG.read_text(encoding="utf-8"))
    catalog = json.loads(REFERENCE_CATALOG.read_text(encoding="utf-8"))
    public_source_count = sum(item.get("access_class") != "restricted_pii" for item in source["documents"])
    payloads = {
        "phase2_reference_counts.json": {
            "catalog_version": catalog["catalog_version"],
            "counts": counts,
            "public_source_document_count": public_source_count,
        },
        "phase2_catalog_checksums.json": {
            "source_documents_catalog": sha256(SOURCE_CATALOG),
            "reference_catalog": sha256(REFERENCE_CATALOG),
        },
        "phase2_migration_catalog.json": [
            {"version": item.version, "name": item.name, "checksum": item.checksum, "destructive_down": item.destructive_down}
            for item in MIGRATIONS
        ],
        "phase2_source_registry.json": {
            "catalog_version": source["catalog_version"],
            "documents": [
                {
                    "id": item["id"], "category": item["category"], "title": item["title"],
                    "organization": item["organization"], "sha256": item["sha256"],
                    "access_class": item["access_class"],
                }
                for item in source["documents"]
            ],
        },
    }
    for filename, payload in payloads.items():
        (destination / filename).write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print("Phase 2 manifests exported")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
