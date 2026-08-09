from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data_foundation.repository import summary
from app.data_foundation.seeding import seed_reference_data
from app.storage.database import initialize_database


def main() -> int:
    initialize_database()
    seeded = seed_reference_data()
    print(json.dumps({"seeded_or_updated": seeded, "database_counts": summary()}, indent=2))
    print("PHASE 2 DATA FOUNDATION INITIALIZED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
