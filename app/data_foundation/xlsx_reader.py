from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator
from xml.etree import ElementTree as ET
from zipfile import ZipFile

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CELL_REF = re.compile(r"([A-Z]+)(\d+)")


@dataclass(frozen=True, slots=True)
class WorkbookRow:
    sheet_name: str
    row_number: int
    values: dict[str, Any]


def _column_index(reference: str) -> int:
    match = CELL_REF.fullmatch(reference)
    if not match:
        raise ValueError(f"Invalid XLSX cell reference: {reference}")
    result = 0
    for char in match.group(1):
        result = result * 26 + (ord(char) - 64)
    return result - 1


def _shared_strings(archive: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    result: list[str] = []
    for item in root.findall(f"{{{MAIN_NS}}}si"):
        result.append("".join(node.text or "" for node in item.iter(f"{{{MAIN_NS}}}t")))
    return result


def _sheet_paths(archive: ZipFile) -> list[tuple[str, str]]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    targets = {
        item.attrib["Id"]: item.attrib["Target"]
        for item in relationships.findall(f"{{{PKG_REL_NS}}}Relationship")
    }
    sheets: list[tuple[str, str]] = []
    sheet_parent = workbook.find(f"{{{MAIN_NS}}}sheets")
    if sheet_parent is None:
        return sheets
    for sheet in sheet_parent:
        relationship_id = sheet.attrib[f"{{{REL_NS}}}id"]
        target = targets[relationship_id].lstrip("/")
        if not target.startswith("xl/"):
            target = f"xl/{target}"
        sheets.append((sheet.attrib["name"], target))
    return sheets


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> Any:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        inline = cell.find(f"{{{MAIN_NS}}}is")
        if inline is None:
            return None
        return "".join(node.text or "" for node in inline.iter(f"{{{MAIN_NS}}}t"))
    value_node = cell.find(f"{{{MAIN_NS}}}v")
    if value_node is None or value_node.text is None:
        return None
    raw = value_node.text
    if cell_type == "s":
        return shared_strings[int(raw)]
    if cell_type == "b":
        return raw == "1"
    if cell_type in {"str", "e"}:
        return raw
    try:
        number = float(raw)
        return int(number) if number.is_integer() else number
    except ValueError:
        return raw


def iter_workbook_rows(path: Path | str) -> Iterator[WorkbookRow]:
    workbook_path = Path(path)
    if not workbook_path.exists():
        raise FileNotFoundError(workbook_path)
    with ZipFile(workbook_path) as archive:
        shared = _shared_strings(archive)
        for sheet_name, sheet_path in _sheet_paths(archive):
            with archive.open(sheet_path) as stream:
                headers: list[str] | None = None
                for event, element in ET.iterparse(stream, events=("end",)):
                    if element.tag != f"{{{MAIN_NS}}}row":
                        continue
                    row_number = int(element.attrib.get("r", "0"))
                    cells: dict[int, Any] = {}
                    for cell in element.findall(f"{{{MAIN_NS}}}c"):
                        reference = cell.attrib.get("r")
                        if not reference:
                            continue
                        cells[_column_index(reference)] = _cell_value(cell, shared)
                    width = max(cells, default=-1) + 1
                    row_values = [cells.get(index) for index in range(width)]
                    if headers is None:
                        headers = [str(value).strip() if value is not None else f"column_{index + 1}" for index, value in enumerate(row_values)]
                    else:
                        values = {headers[index]: row_values[index] if index < len(row_values) else None for index in range(len(headers))}
                        if any(value not in (None, "") for value in values.values()):
                            yield WorkbookRow(sheet_name=sheet_name, row_number=row_number, values=values)
                    element.clear()
