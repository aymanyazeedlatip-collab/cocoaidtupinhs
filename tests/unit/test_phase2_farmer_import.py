from __future__ import annotations

from contextlib import closing

import json
import sqlite3

from app.data_foundation.farmer_import import import_farmer_workbook
from app.data_foundation.repository import farmer_registry_summary, summary
from app.data_foundation.seeding import seed_reference_data
from app.storage.migrations import MigrationManager
from tests.xlsx_factory import create_inline_xlsx

HEADERS = [
    "Region", "Province", "Municipality", "Barangay", "Lastname", "Firstname",
    "Middlename", "Suffix", "Gender", "Absolutearea", "Coconutarea",
    "No. of Trees", "No. of Parcel",
]


def test_farmer_import_quarantines_raw_data_and_separates_identities(tmp_path):
    database = tmp_path / "phase2.sqlite3"
    MigrationManager(database).upgrade()
    seed_reference_data(database_path=database)
    workbook = create_inline_xlsx(
        tmp_path / "farmers.xlsx",
        {"SANTO NIÑO": [
            HEADERS,
            ["XII", "South Cotabato", "SANTO NIÃ‘O", "A", "DELA CRUZ", "ANA", None, None, "FEMALE", 2, 1, 80, 1],
            ["XII", "South Cotabato", "SANTO NIÃ‘O", "A", "DELA CRUZ", "ANA", None, None, "FEMALE", 2, 1, 80, 1],
            ["XII", "South Cotabato", "T\\'BOLI", "B", "TEST", "ZERO", None, None, "MALE", 1, 1, 0, 1],
            ["XII", "South Cotabato", "TUPI", "C", "BAD", "COUNT", None, None, "MALE", 2, 2, 10.5, 1],
            ["XII", "South Cotabato", "TUPI", "D", "BAD", "NEGATIVE", None, None, "MALE", -1, -0.5, -2, 1],
        ]},
    )
    dry = import_farmer_workbook(workbook, database_path=database, dry_run=True)
    assert dry.total_rows == 5
    assert dry.import_run_id is None
    assert summary(database_path=database)["farmer_registry_records"] == 0

    result = import_farmer_workbook(workbook, database_path=database)
    assert result.total_rows == 5
    assert result.duplicate_groups == 1
    assert result.rejected_rows == 2
    assert result.flag_counts["possible_duplicate_identity"] == 2
    assert result.flag_counts["positive_coconut_area_zero_trees"] == 2
    assert result.flag_counts["non_integer_count"] == 1

    public = farmer_registry_summary(database_path=database)
    assert public["total_records"] == 5
    serialized = json.dumps(public).lower()
    assert "dela cruz" not in serialized
    assert "ana" not in serialized
    with closing(sqlite3.connect(database)) as conn:
        conn.row_factory = sqlite3.Row
        identities = conn.execute("SELECT last_name, first_name FROM farmer_identities ORDER BY source_row_number").fetchall()
        registry_columns = {row[1] for row in conn.execute("PRAGMA table_info(farmer_registry)")}
        municipalities = [row[0] for row in conn.execute("SELECT municipality FROM farmer_registry ORDER BY source_row_number")]
        assert identities[0]["last_name"] == "DELA CRUZ"
        assert "last_name" not in registry_columns and "first_name" not in registry_columns
        assert municipalities[:2] == ["SANTO NIÑO", "SANTO NIÑO"]
        assert municipalities[2] == "T'BOLI"
        negative = conn.execute("SELECT absolute_area_hectares, coconut_area_hectares, tree_count FROM farmer_registry WHERE source_row_number = 6").fetchone()
        assert tuple(negative) == (None, None, None)
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []

    reused = import_farmer_workbook(workbook, database_path=database)
    assert reused.reused_existing_run is True
    assert summary(database_path=database)["farmer_registry_records"] == 5
