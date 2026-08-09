from __future__ import annotations

import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings
from app.storage.database import initialize_database


@pytest.fixture(autouse=True)
def isolated_db(tmp_path):
    original = settings.database_path
    original_reports = settings.reports_dir
    settings.database_path = tmp_path / "test.sqlite3"
    settings.reports_dir = tmp_path / "reports"
    initialize_database()
    yield
    settings.database_path = original
    settings.reports_dir = original_reports
