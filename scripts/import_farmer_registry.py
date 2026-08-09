from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings
from app.data_foundation.farmer_import import import_farmer_workbook
from app.data_foundation.seeding import seed_reference_data
from app.storage.database import initialize_database


def main() -> int:
    parser = argparse.ArgumentParser(description="Import the restricted PCA farmer workbook into quarantined and analytical tables")
    parser.add_argument(
        "workbook",
        nargs="?",
        default=str(ROOT / "data_sources" / "raw" / "farmers" / "Farmers_Lists_Updated.xlsx"),
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate and summarize without storing farmer records")
    parser.add_argument("--force", action="store_true", help="Create a new import run even if this exact workbook was already imported")
    args = parser.parse_args()

    initialize_database()
    seed_reference_data()
    result = import_farmer_workbook(
        Path(args.workbook),
        database_path=settings.database_path,
        dry_run=args.dry_run,
        reuse_existing=not args.force,
    )
    print(json.dumps(result.as_dict(), indent=2, ensure_ascii=False))
    if result.status == "dry_run":
        print("DRY RUN COMPLETE: no farmer records were stored")
    elif result.reused_existing_run:
        print("WORKBOOK ALREADY IMPORTED: existing completed run reused")
    else:
        print("FARMER REGISTRY IMPORT COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
