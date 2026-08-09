from __future__ import annotations

from app.data_foundation.xlsx_reader import iter_workbook_rows
from tests.xlsx_factory import create_inline_xlsx


def test_xlsx_reader_streams_multiple_inline_string_sheets(tmp_path):
    workbook = create_inline_xlsx(
        tmp_path / "sample.xlsx",
        {
            "First": [["Name", "Count", "Active"], ["Alpha", 12, True], ["Beta", 4.5, False]],
            "Second": [["Name", "Count", "Active"], ["Gamma", 7, True]],
        },
    )
    rows = list(iter_workbook_rows(workbook))
    assert [(row.sheet_name, row.row_number) for row in rows] == [("First", 2), ("First", 3), ("Second", 2)]
    assert rows[0].values == {"Name": "Alpha", "Count": 12, "Active": True}
    assert rows[1].values["Count"] == 4.5
