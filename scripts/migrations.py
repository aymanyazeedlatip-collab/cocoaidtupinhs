from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings
from app.storage.migrations import MigrationManager


def main() -> int:
    parser = argparse.ArgumentParser(description="COCOAID SQLite migration manager")
    parser.add_argument("command", choices=["status", "upgrade", "downgrade-one"])
    parser.add_argument("--target", type=int, default=None, help="Target schema version for upgrade")
    parser.add_argument("--allow-destructive", action="store_true", help="Allow destructive rollback")
    args = parser.parse_args()

    manager = MigrationManager(settings.database_path)
    if args.command == "status":
        print(json.dumps([asdict(item) for item in manager.status()], indent=2))
        return 0
    if args.command == "upgrade":
        applied = manager.upgrade(args.target)
        print(json.dumps({"applied_versions": applied, "database": str(settings.database_path)}, indent=2))
        return 0
    version = manager.downgrade_one(allow_destructive=args.allow_destructive)
    print(json.dumps({"rolled_back_version": version, "database": str(settings.database_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
