from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.data_foundation.repository import connection
from app.data_foundation.xlsx_reader import WorkbookRow, iter_workbook_rows

EXPECTED_COLUMNS = (
    "Region", "Province", "Municipality", "Barangay", "Lastname", "Firstname",
    "Middlename", "Suffix", "Gender", "Absolutearea", "Coconutarea", "No. of Trees", "No. of Parcel",
)


@dataclass(frozen=True, slots=True)
class QualityFlag:
    code: str
    severity: str
    field_name: str | None
    observed_value: Any
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "field_name": self.field_name,
            "observed_value": self.observed_value,
            "message": self.message,
        }


@dataclass(slots=True)
class PreparedFarmerRow:
    source_sheet: str
    source_row_number: int
    raw: dict[str, Any]
    normalized: dict[str, Any]
    flags: list[QualityFlag] = field(default_factory=list)
    identity_fingerprint: str = ""
    duplicate_group_hash: str | None = None
    status: str = "accepted"


@dataclass(frozen=True, slots=True)
class FarmerImportResult:
    import_run_id: str | None
    source_sha256: str
    status: str
    sheet_count: int
    total_rows: int
    accepted_rows: int
    flagged_rows: int
    rejected_rows: int
    duplicate_groups: int
    error_count: int
    flag_counts: dict[str, int]
    municipality_counts: dict[str, int]
    reused_existing_run: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "import_run_id": self.import_run_id,
            "source_sha256": self.source_sha256,
            "status": self.status,
            "sheet_count": self.sheet_count,
            "total_rows": self.total_rows,
            "accepted_rows": self.accepted_rows,
            "flagged_rows": self.flagged_rows,
            "rejected_rows": self.rejected_rows,
            "duplicate_groups": self.duplicate_groups,
            "error_count": self.error_count,
            "flag_counts": self.flag_counts,
            "municipality_counts": self.municipality_counts,
            "reused_existing_run": self.reused_existing_run,
        }


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    if not text:
        return None
    # Conservative repair for common UTF-8-as-Latin-1 artifacts. Only accept a repair
    # when the original contains a strong mojibake marker.
    if any(marker in text for marker in ("Ã", "Â", "â€")):
        for source_encoding in ("cp1252", "latin-1"):
            try:
                repaired = text.encode(source_encoding).decode("utf-8")
                if repaired:
                    text = repaired
                    break
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue
    # Some source cells contain a literal backslash before an apostrophe. This is
    # an encoding artifact, not a semantic location correction.
    text = text.replace("\\'", "'")
    return text


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = str(value).strip().replace(",", "")
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _integer(value: Any) -> int | None:
    number = _number(value)
    if number is None:
        return None
    if not number.is_integer():
        return None
    return int(number)


def _normalized_identity(row: dict[str, Any]) -> str:
    fields = [
        _clean_text(row.get("Lastname")), _clean_text(row.get("Firstname")),
        _clean_text(row.get("Middlename")), _clean_text(row.get("Suffix")),
        _clean_text(row.get("Municipality")), _clean_text(row.get("Barangay")),
    ]
    return "|".join((item or "").casefold() for item in fields)


def _fingerprint(secret: str, material: str) -> str:
    return hashlib.sha256(f"{secret}:{material}".encode("utf-8")).hexdigest()


def _get_or_create_privacy_secret(conn) -> str:
    row = conn.execute("SELECT value FROM system_metadata WHERE key = 'farmer_privacy_secret'").fetchone()
    if row:
        return str(row[0])
    value = secrets.token_hex(32)
    conn.execute(
        "INSERT INTO system_metadata(key, value, updated_at) VALUES ('farmer_privacy_secret', ?, ?)",
        (value, _now()),
    )
    return value


def _prepare(row: WorkbookRow, secret: str) -> PreparedFarmerRow:
    raw = {column: row.values.get(column) for column in EXPECTED_COLUMNS}
    normalized = {
        "region": _clean_text(raw["Region"]),
        "province": _clean_text(raw["Province"]),
        "municipality": _clean_text(raw["Municipality"]),
        "barangay": _clean_text(raw["Barangay"]),
        "last_name": _clean_text(raw["Lastname"]),
        "first_name": _clean_text(raw["Firstname"]),
        "middle_name": _clean_text(raw["Middlename"]),
        "suffix": _clean_text(raw["Suffix"]),
        "gender": (_clean_text(raw["Gender"]) or "").upper() or None,
        "absolute_area_hectares": _number(raw["Absolutearea"]),
        "coconut_area_hectares": _number(raw["Coconutarea"]),
        "tree_count": _integer(raw["No. of Trees"]),
        "parcel_count": _integer(raw["No. of Parcel"]),
    }
    flags: list[QualityFlag] = []
    for field_name in ("region", "province", "municipality", "barangay"):
        if not normalized[field_name]:
            flags.append(QualityFlag("missing_location", "error", field_name, None, f"{field_name} is required"))
    if not normalized["last_name"] and not normalized["first_name"]:
        flags.append(QualityFlag("missing_identity_name", "error", "name", None, "At least one name field is required"))
    for field_name in ("absolute_area_hectares", "coconut_area_hectares"):
        value = normalized[field_name]
        if value is not None and value < 0:
            flags.append(QualityFlag("negative_area", "error", field_name, value, "Area cannot be negative"))
            # The raw value remains in quarantine; the analytical field is nulled so
            # a rejected row can still be audited without violating schema bounds.
            normalized[field_name] = None
    for source_name, field_name in (("No. of Trees", "tree_count"), ("No. of Parcel", "parcel_count")):
        source_value = raw[source_name]
        if source_value not in (None, "") and normalized[field_name] is None:
            flags.append(QualityFlag("non_integer_count", "error", field_name, source_value, "Count must be a whole number"))
        elif normalized[field_name] is not None and normalized[field_name] < 0:
            flags.append(QualityFlag("negative_count", "error", field_name, normalized[field_name], "Count cannot be negative"))
            normalized[field_name] = None

    absolute = normalized["absolute_area_hectares"]
    coconut = normalized["coconut_area_hectares"]
    trees = normalized["tree_count"]
    if absolute is not None and coconut is not None and coconut > absolute:
        flags.append(QualityFlag("coconut_area_exceeds_absolute_area", "warning", "coconut_area_hectares", coconut, "Coconut area exceeds declared absolute area"))
    if absolute == 0 and coconut is not None and coconut > 0:
        flags.append(QualityFlag("zero_absolute_area_positive_coconut_area", "error", "absolute_area_hectares", absolute, "Positive coconut area with zero absolute area"))
    if coconut is not None and coconut > 0 and (trees is None or trees == 0):
        flags.append(QualityFlag("positive_coconut_area_zero_trees", "warning", "tree_count", trees, "Positive coconut area but no trees recorded"))
    if trees is not None and trees > 0 and (coconut is None or coconut == 0):
        flags.append(QualityFlag("positive_trees_zero_coconut_area", "warning", "coconut_area_hectares", coconut, "Trees recorded but coconut area is zero or missing"))
    density = None
    if coconut is not None and coconut > 0 and trees is not None:
        density = trees / coconut
        if density > 1000:
            flags.append(QualityFlag("tree_density_over_1000_per_ha", "warning", "tree_density_per_hectare", round(density, 4), "Tree density exceeds 1,000 palms per hectare"))
        elif 0 < density < 10:
            flags.append(QualityFlag("tree_density_below_10_per_ha", "warning", "tree_density_per_hectare", round(density, 4), "Tree density is below 10 palms per hectare"))
    normalized["tree_density_per_hectare"] = density
    identity_material = _normalized_identity(raw)
    identity_fingerprint = _fingerprint(secret, identity_material)
    status = "rejected" if any(flag.severity == "error" for flag in flags) else ("flagged" if flags else "accepted")
    return PreparedFarmerRow(
        source_sheet=row.sheet_name,
        source_row_number=row.row_number,
        raw=raw,
        normalized=normalized,
        flags=flags,
        identity_fingerprint=identity_fingerprint,
        status=status,
    )


def _result_from_rows(rows: list[PreparedFarmerRow], source_sha256: str, import_run_id: str | None, status: str, *, reused: bool = False) -> FarmerImportResult:
    sheets = {row.source_sheet for row in rows}
    flag_counts = Counter(flag.code for row in rows for flag in row.flags)
    municipality_counts = Counter((row.normalized.get("municipality") or "UNKNOWN") for row in rows)
    duplicate_counts = Counter(row.duplicate_group_hash for row in rows if row.duplicate_group_hash)
    return FarmerImportResult(
        import_run_id=import_run_id,
        source_sha256=source_sha256,
        status=status,
        sheet_count=len(sheets),
        total_rows=len(rows),
        accepted_rows=sum(row.status == "accepted" for row in rows),
        flagged_rows=sum(row.status == "flagged" for row in rows),
        rejected_rows=sum(row.status == "rejected" for row in rows),
        duplicate_groups=sum(count > 1 for count in duplicate_counts.values()),
        error_count=sum(flag.severity == "error" for row in rows for flag in row.flags),
        flag_counts=dict(sorted(flag_counts.items())),
        municipality_counts=dict(sorted(municipality_counts.items())),
        reused_existing_run=reused,
    )


def import_farmer_workbook(
    workbook_path: Path | str,
    *,
    database_path: Path | None = None,
    source_document_id: str = "pca-farmer-registry",
    dry_run: bool = False,
    reuse_existing: bool = True,
) -> FarmerImportResult:
    path = Path(workbook_path)
    source_sha256 = _sha256(path)
    with connection(database_path) as conn:
        existing = conn.execute(
            """SELECT id, summary_json FROM farmer_import_runs
               WHERE source_sha256 = ? AND status = 'completed' ORDER BY completed_at DESC LIMIT 1""",
            (source_sha256,),
        ).fetchone()
        if existing and reuse_existing and not dry_run:
            stored = json.loads(existing["summary_json"])
            return FarmerImportResult(**stored, reused_existing_run=True)
        secret = _get_or_create_privacy_secret(conn)

    rows = [_prepare(row, secret) for row in iter_workbook_rows(path)]
    identity_counts = Counter(row.identity_fingerprint for row in rows)
    for row in rows:
        if identity_counts[row.identity_fingerprint] > 1:
            row.duplicate_group_hash = row.identity_fingerprint
            row.flags.append(QualityFlag("possible_duplicate_identity", "warning", "identity", None, "Same normalized identity and location appears more than once"))
            if row.status == "accepted":
                row.status = "flagged"

    if dry_run:
        return _result_from_rows(rows, source_sha256, None, "dry_run")

    import_run_id = str(uuid.uuid4())
    started = _now()
    with connection(database_path) as conn:
        conn.execute(
            """INSERT INTO farmer_import_runs
               (id, source_document_id, source_sha256, started_at, status, summary_json)
               VALUES (?, ?, ?, ?, 'running', '{}')""",
            (import_run_id, source_document_id, source_sha256, started),
        )
        for row in rows:
            stable_material = f"{source_sha256}:{row.source_sheet}:{row.source_row_number}"
            staging_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"cocoaid:staging:{stable_material}"))
            identity_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"cocoaid:identity:{stable_material}"))
            registry_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"cocoaid:registry:{stable_material}"))
            conn.execute(
                """INSERT INTO farmer_registry_staging
                   (id, import_run_id, source_sheet, source_row_number, raw_payload_json,
                    normalized_payload_json, quality_flags_json, duplicate_group_hash, imported_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (staging_id, import_run_id, row.source_sheet, row.source_row_number,
                 json.dumps(row.raw, ensure_ascii=False, default=str),
                 json.dumps(row.normalized, ensure_ascii=False, default=str),
                 json.dumps([flag.as_dict() for flag in row.flags], ensure_ascii=False, default=str),
                 row.duplicate_group_hash, started),
            )
            n = row.normalized
            conn.execute(
                """INSERT INTO farmer_identities
                   (id, import_run_id, source_sheet, source_row_number, last_name, first_name,
                    middle_name, suffix, gender, identity_fingerprint, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (identity_id, import_run_id, row.source_sheet, row.source_row_number, n["last_name"],
                 n["first_name"], n["middle_name"], n["suffix"], n["gender"], row.identity_fingerprint, started),
            )
            conn.execute(
                """INSERT INTO farmer_registry
                   (id, identity_id, import_run_id, source_sheet, source_row_number, region, province,
                    municipality, barangay, absolute_area_hectares, coconut_area_hectares, tree_count,
                    parcel_count, tree_density_per_hectare, data_quality_status, duplicate_group_hash, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (registry_id, identity_id, import_run_id, row.source_sheet, row.source_row_number, n["region"],
                 n["province"], n["municipality"], n["barangay"], n["absolute_area_hectares"],
                 n["coconut_area_hectares"], n["tree_count"], n["parcel_count"], n["tree_density_per_hectare"],
                 row.status, row.duplicate_group_hash, started),
            )
            for index, flag in enumerate(row.flags, start=1):
                flag_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"cocoaid:quality:{stable_material}:{index}:{flag.code}"))
                conn.execute(
                    """INSERT INTO farmer_quality_flags
                       (id, farmer_registry_id, flag_code, severity, field_name, observed_value, message, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (flag_id, registry_id, flag.code, flag.severity, flag.field_name,
                     None if flag.observed_value is None else str(flag.observed_value), flag.message, started),
                )

        result = _result_from_rows(rows, source_sha256, import_run_id, "completed")
        summary_payload = result.as_dict()
        summary_payload.pop("reused_existing_run", None)
        conn.execute(
            """UPDATE farmer_import_runs SET completed_at = ?, status = 'completed', sheet_count = ?,
               total_rows = ?, accepted_rows = ?, flagged_rows = ?, duplicate_groups = ?, error_count = ?,
               summary_json = ? WHERE id = ?""",
            (_now(), result.sheet_count, result.total_rows, result.accepted_rows, result.flagged_rows,
             result.duplicate_groups, result.error_count, json.dumps(summary_payload, sort_keys=True), import_run_id),
        )
    return result
