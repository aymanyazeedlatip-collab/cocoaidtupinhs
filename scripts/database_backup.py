from __future__ import annotations

from contextlib import closing

import argparse
import shutil
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings


def backup(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(source)) as src, closing(sqlite3.connect(destination)) as dst:
        src.backup(dst)


def restore(source: Path, destination: Path, *, confirm: bool) -> None:
    if not confirm:
        raise SystemExit("Restore overwrites the destination. Re-run with --confirm-overwrite.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".restore.tmp")
    shutil.copy2(source, temporary)
    with closing(sqlite3.connect(temporary)) as conn:
        result = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            temporary.unlink(missing_ok=True)
            raise RuntimeError(f"Backup integrity check failed: {result}")
    temporary.replace(destination)


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup or restore the COCOAID SQLite database")
    sub = parser.add_subparsers(dest="command", required=True)
    p_backup = sub.add_parser("backup")
    p_backup.add_argument("--output", default=None)
    p_restore = sub.add_parser("restore")
    p_restore.add_argument("backup_file")
    p_restore.add_argument("--confirm-overwrite", action="store_true")
    args = parser.parse_args()

    database = settings.database_path
    if args.command == "backup":
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        output = Path(args.output) if args.output else ROOT / "backups" / f"coco_aid_{stamp}.sqlite3"
        if not database.exists():
            raise FileNotFoundError(database)
        backup(database, output)
        print(f"Backup created: {output}")
        return 0
    source = Path(args.backup_file)
    restore(source, database, confirm=args.confirm_overwrite)
    print(f"Database restored from: {source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
