from __future__ import annotations

import ast
import hashlib
import json
import re
import sqlite3
import subprocess
import warnings
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = ROOT / "manifests"
DOCS = ROOT / "docs" / "phase_0"
BASELINE_TAG = "v2.11-legacy-baseline"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    def clean(value: Any) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")
    output = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    output.extend("| " + " | ".join(clean(item) for item in row) + " |" for row in rows)
    return "\n".join(output)


def git_files_at_tag(tag: str) -> list[str]:
    result = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", tag],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def git_blob_at_tag(tag: str, relative: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{tag}:{relative}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return result.stdout


def baseline_manifest() -> dict[str, Any]:
    files = []
    total = 0
    for relative in git_files_at_tag(BASELINE_TAG):
        content = git_blob_at_tag(BASELINE_TAG, relative)
        size = len(content)
        total += size
        files.append({"path": relative, "size_bytes": size, "sha256": hashlib.sha256(content).hexdigest()})
    return {
        "baseline_tag": BASELINE_TAG,
        "generated_at": datetime.now(UTC).isoformat(),
        "file_count": len(files),
        "total_size_bytes": total,
        "files": files,
    }


def decorator_endpoint(node: ast.FunctionDef | ast.AsyncFunctionDef, source: str) -> list[dict[str, Any]]:
    endpoints: list[dict[str, Any]] = []
    for decorator in node.decorator_list:
        if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
            continue
        owner = decorator.func.value
        if not isinstance(owner, ast.Name) or owner.id not in {"router", "app"}:
            continue
        method = decorator.func.attr.upper()
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}:
            continue
        path = None
        if decorator.args and isinstance(decorator.args[0], ast.Constant):
            path = decorator.args[0].value
        if not isinstance(path, str):
            continue
        if owner.id == "router":
            path = "/api" + path
        endpoints.append({
            "method": method,
            "path": path,
            "function": node.name,
            "source": source,
            "line": node.lineno,
            "async": isinstance(node, ast.AsyncFunctionDef),
        })
    return endpoints


def endpoint_inventory() -> list[dict[str, Any]]:
    endpoints: list[dict[str, Any]] = []
    for relative in ("app/main.py", "app/api/routes.py"):
        path = ROOT / relative
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                endpoints.extend(decorator_endpoint(node, relative))
    return sorted(endpoints, key=lambda row: (row["path"], row["method"]))


def class_inventory(relative: str) -> list[dict[str, Any]]:
    path = ROOT / relative
    tree = ast.parse(path.read_text(encoding="utf-8"))
    result = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        fields = []
        methods = []
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                fields.append(item.target.id)
            elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(item.name)
        result.append({"class": node.name, "line": node.lineno, "fields": fields, "methods": methods})
    return result


def schema_inventory() -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for path in sorted((ROOT / "app" / "schemas").glob("*.py")):
        if path.name == "__init__.py":
            continue
        payload[str(path.relative_to(ROOT))] = class_inventory(str(path.relative_to(ROOT)))
    return payload


def database_inventory() -> dict[str, Any]:
    path = ROOT / "data" / "coco_aid.sqlite3"
    if not path.exists():
        return {"path": str(path.relative_to(ROOT)), "exists": False, "tables": []}
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        tables = []
        for row in connection.execute("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name"):
            columns = [dict(item) for item in connection.execute(f"PRAGMA table_info('{row['name']}')")]
            indexes = [dict(item) for item in connection.execute(f"PRAGMA index_list('{row['name']}')")]
            count = int(connection.execute(f"SELECT COUNT(*) FROM '{row['name']}'").fetchone()[0])
            tables.append({"name": row["name"], "row_count": count, "columns": columns, "indexes": indexes, "sql": row["sql"]})
        return {"path": str(path.relative_to(ROOT)), "exists": True, "size_bytes": path.stat().st_size, "tables": tables}
    finally:
        connection.close()


def model_inventory() -> list[dict[str, Any]]:
    rows = []
    for path in sorted((ROOT / "artifacts" / "models").glob("*.joblib")):
        name = path.stem.replace("_model", "")
        card_path = ROOT / "artifacts" / "model_cards" / f"{name.upper()}_MODEL_CARD.json"
        card = json.loads(card_path.read_text(encoding="utf-8")) if card_path.exists() else {}
        row: dict[str, Any] = {
            "name": name,
            "path": str(path.relative_to(ROOT)),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "card": card,
        }
        try:
            import joblib
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                artifact = joblib.load(path)
            row.update({
                "artifact_type": type(artifact).__name__,
                "artifact_version": artifact.get("version") if isinstance(artifact, dict) else None,
                "features": artifact.get("features", []) if isinstance(artifact, dict) else [],
                "pipeline_type": type(artifact.get("pipeline")).__name__ if isinstance(artifact, dict) else None,
                "load_warnings": sorted({str(item.message) for item in caught}),
            })
        except Exception as exc:
            row["load_error"] = f"{type(exc).__name__}: {exc}"
        rows.append(row)
    return rows


def code_metrics() -> dict[str, Any]:
    extensions = {".py", ".js", ".css", ".html", ".md", ".json"}
    rows = []
    for relative in git_files_at_tag(BASELINE_TAG):
        suffix = Path(relative).suffix.lower()
        if suffix not in extensions:
            continue
        content = git_blob_at_tag(BASELINE_TAG, relative)
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            continue
        rows.append({
            "path": relative,
            "extension": suffix,
            "lines": len(text.splitlines()),
            "size_bytes": len(content),
        })
    rows.sort(key=lambda item: item["lines"], reverse=True)
    by_extension: dict[str, dict[str, int]] = {}
    for row in rows:
        bucket = by_extension.setdefault(row["extension"], {"files": 0, "lines": 0})
        bucket["files"] += 1
        bucket["lines"] += row["lines"]
    return {"files": rows, "by_extension": by_extension}


def frontend_inventory() -> dict[str, Any]:
    html_path = ROOT / "app" / "static" / "index.html"
    js_path = ROOT / "app" / "static" / "app.js"
    css_path = ROOT / "app" / "static" / "styles.css"
    html = html_path.read_text(encoding="utf-8")
    js = js_path.read_text(encoding="utf-8")
    ids = sorted(set(re.findall(r'\bid=["\']([^"\']+)["\']', html)))
    functions = sorted(set(
        re.findall(r"(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(", js)
        + re.findall(r"\b(?:const|let)\s+([A-Za-z_$][\w$]*)\s*=\s*async\s*\(", js)
        + re.findall(r"\b(?:const|let)\s+([A-Za-z_$][\w$]*)\s*=\s*\([^)]*\)\s*=>", js)
    ))
    return {
        "main_html": {"path": str(html_path.relative_to(ROOT)), "lines": len(html.splitlines()), "element_id_count": len(ids), "element_ids": ids},
        "main_javascript": {"path": str(js_path.relative_to(ROOT)), "lines": len(js.splitlines()), "named_function_count": len(functions), "named_functions": functions},
        "main_stylesheet": {"path": str(css_path.relative_to(ROOT)), "lines": len(css_path.read_text(encoding="utf-8").splitlines())},
    }


def test_inventory() -> dict[str, Any]:
    files = []
    total_tests = 0
    for path in sorted((ROOT / "tests").rglob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        tests = [node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")]
        total_tests += len(tests)
        files.append({"path": str(path.relative_to(ROOT)), "test_count": len(tests), "tests": sorted(tests)})
    return {"file_count": len(files), "test_function_count": total_tests, "files": files}


def raw_source_inventory() -> list[dict[str, Any]]:
    root = ROOT / "data_sources" / "raw"
    if not root.exists():
        return []
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rows.append({"path": str(path.relative_to(ROOT)), "size_bytes": path.stat().st_size, "sha256": sha256_file(path), "extension": path.suffix.lower()})
    return rows


def write_docs(endpoints: list[dict[str, Any]], models: list[dict[str, Any]], database: dict[str, Any], metrics: dict[str, Any], frontend: dict[str, Any], tests: dict[str, Any]) -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    api_rows = [[item["method"], f"`{item['path']}`", f"`{item['function']}`", f"{item['source']}:{item['line']}"] for item in endpoints]
    (DOCS / "API_INVENTORY.md").write_text(
        "# Legacy API Inventory\n\n"
        f"The frozen v2.11 baseline exposes **{len(endpoints)}** decorated HTTP routes, including static application routes.\n\n"
        + md_table(["Method", "Path", "Handler", "Source"], api_rows) + "\n",
        encoding="utf-8",
    )

    model_rows = []
    for item in models:
        card = item.get("card", {})
        metrics_text = ", ".join(f"{key}={value:.4g}" if isinstance(value, float) else f"{key}={value}" for key, value in card.get("metrics", {}).items() if not isinstance(value, list))
        model_rows.append([item["name"], item.get("artifact_version"), card.get("data_source_type"), len(item.get("features", [])), metrics_text, item["sha256"][:16] + "…"])
    (DOCS / "MODEL_INVENTORY.md").write_text(
        "# Legacy Model Inventory\n\n"
        "All three bundled models are preserved without retraining. Their model cards explicitly identify the training data as synthetic/reference-based, so they remain baseline prototype models pending field validation.\n\n"
        + md_table(["Model", "Artifact version", "Data source", "Features", "Card metrics", "SHA-256"], model_rows)
        + "\n\n## Compatibility risk\n\nThe artifacts were serialized with scikit-learn 1.9.0 while the current audit environment loaded scikit-learn 1.8.0. The test suite passes, but the resulting `InconsistentVersionWarning` is a release-blocking reproducibility risk for Phase 1.\n",
        encoding="utf-8",
    )

    db_rows = [[table["name"], table["row_count"], ", ".join(column["name"] for column in table["columns"])] for table in database.get("tables", [])]
    (DOCS / "DATABASE_INVENTORY.md").write_text(
        "# Legacy Database Inventory\n\n"
        "The v2.11 SQLite schema stores the principal farm, analysis, and forecast objects as JSON payloads. This supports rapid prototyping but prevents normalized provenance, relational queries, and independent versioning of observations and model runs.\n\n"
        + md_table(["Table", "Rows in supplied baseline", "Columns"], db_rows)
        + "\n\nThe supplied database contains no saved farm, analysis, report, or forecast records, so the v3 migration can be designed without transforming existing user rows in this specific package. Migration support will still be implemented for compatibility with other installations.\n",
        encoding="utf-8",
    )

    top = metrics["files"][:20]
    metric_rows = [[item["path"], item["lines"], item["extension"]] for item in top]
    (DOCS / "SYSTEM_INVENTORY.md").write_text(
        "# Legacy System Inventory\n\n"
        "## Baseline\n\n"
        "- Product version: COCO-AID 2.11.0\n"
        "- Backend: FastAPI and Pydantic\n"
        "- Persistence: SQLite with JSON payload columns\n"
        "- Frontend: static HTML, CSS, and vanilla JavaScript\n"
        "- Analytical components: production, pest, suitability, climate projection, stochastic farm simulation, rehabilitation mapping, reports, and optional Gemini assistant\n"
        f"- Automated tests discovered: {tests['test_function_count']} test functions across {tests['file_count']} files\n"
        f"- API routes discovered: {len(endpoints)}\n\n"
        "## Largest text source files\n\n"
        + md_table(["Path", "Lines", "Type"], metric_rows)
        + "\n\n## Coupling observations\n\n"
        f"- `app/static/app.js` contains {frontend['main_javascript']['lines']} lines.\n"
        f"- `app/static/styles.css` contains {frontend['main_stylesheet']['lines']} lines.\n"
        "- `app/api/routes.py` centralizes most HTTP orchestration.\n"
        "- `app/simulation/farm_site_forecast.py` combines weather merging, long-range projection, product calculations, hazard generation, and spatial frame construction.\n"
        "- The new engines must be introduced behind explicit service contracts rather than added to these monoliths.\n",
        encoding="utf-8",
    )

    (DOCS / "FRONTEND_INVENTORY.md").write_text(
        "# Legacy Frontend Inventory\n\n"
        f"- Main HTML: {frontend['main_html']['lines']} lines and {frontend['main_html']['element_id_count']} unique element IDs.\n"
        f"- Main JavaScript: {frontend['main_javascript']['lines']} lines and {frontend['main_javascript']['named_function_count']} detected named functions.\n"
        f"- Main stylesheet: {frontend['main_stylesheet']['lines']} lines.\n\n"
        "The current frontend remains frozen during Phase 0. Phase 1 will define feature boundaries and shared components before any navigation or visual redesign is attempted.\n",
        encoding="utf-8",
    )


def main() -> None:
    MANIFESTS.mkdir(parents=True, exist_ok=True)
    baseline = baseline_manifest()
    endpoints = endpoint_inventory()
    schemas = schema_inventory()
    database = database_inventory()
    models = model_inventory()
    metrics = code_metrics()
    frontend = frontend_inventory()
    tests = test_inventory()
    sources = raw_source_inventory()

    json_write(MANIFESTS / "legacy_baseline_manifest.json", baseline)
    json_write(MANIFESTS / "endpoint_inventory.json", endpoints)
    json_write(MANIFESTS / "schema_inventory.json", schemas)
    json_write(MANIFESTS / "database_inventory.json", database)
    json_write(MANIFESTS / "model_inventory.json", models)
    json_write(MANIFESTS / "model_checksums.json", {item["name"]: {"path": item["path"], "sha256": item["sha256"], "size_bytes": item["size_bytes"]} for item in models})
    json_write(MANIFESTS / "code_metrics.json", metrics)
    json_write(MANIFESTS / "frontend_inventory.json", frontend)
    json_write(MANIFESTS / "test_inventory.json", tests)
    json_write(MANIFESTS / "raw_source_checksums.json", sources)
    write_docs(endpoints, models, database, metrics, frontend, tests)
    print(f"Phase 0 inventory generated: {len(endpoints)} routes, {len(models)} models, {tests['test_function_count']} test functions.")


if __name__ == "__main__":
    main()
