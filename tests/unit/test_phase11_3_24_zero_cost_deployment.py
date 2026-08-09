from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

import httpx

from app.core.config import Settings, settings
from app.services.supabase_state import SupabaseStateStore

ROOT = Path(__file__).resolve().parents[2]


def _configure_store(monkeypatch, tmp_path: Path) -> SupabaseStateStore:
    monkeypatch.setattr(settings, "supabase_state_sync_enabled", True)
    monkeypatch.setattr(settings, "supabase_state_required", True)
    monkeypatch.setattr(settings, "supabase_url", "https://example.supabase.co")
    monkeypatch.setattr(settings, "supabase_secret_key", "sb_secret_test_backend_key")
    monkeypatch.setattr(settings, "supabase_storage_bucket", "cocoaid-state")
    monkeypatch.setattr(settings, "supabase_state_object", "state/coco_aid.sqlite3")
    monkeypatch.setattr(settings, "supabase_state_max_object_bytes", 48 * 1024 * 1024)
    monkeypatch.setattr(settings, "database_path", tmp_path / "coco_aid.sqlite3")
    return SupabaseStateStore()


def test_free_render_blueprint_has_no_paid_resource() -> None:
    text = (ROOT / "render.yaml").read_text(encoding="utf-8")
    assert "plan: free" in text
    assert "plan: standard" not in text
    assert "disk:" not in text
    assert "maxShutdownDelaySeconds" not in text
    assert "SUPABASE_URL" in text and "sync: false" in text
    assert "SUPABASE_SECRET_KEY" in text
    assert "PERSISTENT_DATA_DIR" in text and "/tmp/cocoaid-runtime" in text


def test_old_free_demo_blueprint_removed_to_avoid_confusion() -> None:
    assert not (ROOT / "render.free-demo.yaml").exists()


def test_supabase_settings_are_server_side_and_optional_by_default() -> None:
    local = Settings(_env_file=None)
    assert local.supabase_state_sync_enabled is False
    assert local.supabase_state_required is False
    configured = Settings(
        _env_file=None,
        supabase_state_sync_enabled=True,
        supabase_url="https://abc.supabase.co/",
        supabase_secret_key="sb_secret_example",
    )
    assert configured.supabase_url == "https://abc.supabase.co"
    assert configured.supabase_state_configured is True


def test_secret_key_is_not_forced_into_bearer_header(monkeypatch, tmp_path: Path) -> None:
    store = _configure_store(monkeypatch, tmp_path)
    headers = store._headers()
    assert headers["apikey"] == "sb_secret_test_backend_key"
    assert "Authorization" not in headers
    monkeypatch.setattr(settings, "supabase_secret_key", "legacy.jwt.service-role")
    legacy = store._headers()
    assert legacy["Authorization"] == "Bearer legacy.jwt.service-role"


def test_supabase_database_snapshot_round_trip(monkeypatch, tmp_path: Path) -> None:
    store = _configure_store(monkeypatch, tmp_path)
    db = settings.database_path
    db.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute("INSERT INTO sample(value) VALUES ('persisted')")
        conn.commit()

    uploaded: dict[str, bytes] = {}

    def fake_request(method: str, path: str, **kwargs):
        if method == "GET" and path == "/storage/v1/bucket/cocoaid-state":
            return httpx.Response(200, json={"id": "cocoaid-state"})
        if method == "POST" and path == "/storage/v1/object/cocoaid-state/state/coco_aid.sqlite3":
            uploaded["db"] = kwargs["content"]
            return httpx.Response(200, json={"Key": "state/coco_aid.sqlite3"})
        if method == "GET" and path == "/storage/v1/object/authenticated/cocoaid-state/state/coco_aid.sqlite3":
            return httpx.Response(200, content=uploaded["db"])
        raise AssertionError((method, path))

    monkeypatch.setattr(store, "_request", fake_request)
    assert store.sync_database(force=True) is True
    assert len(uploaded["db"]) > 0

    db.unlink()
    assert store.restore_database() is True
    with closing(sqlite3.connect(db)) as conn:
        row = conn.execute("SELECT value FROM sample").fetchone()
    assert row == ("persisted",)


def test_supabase_bucket_is_created_automatically(monkeypatch, tmp_path: Path) -> None:
    store = _configure_store(monkeypatch, tmp_path)
    calls: list[tuple[str, str, dict]] = []

    def fake_request(method: str, path: str, **kwargs):
        calls.append((method, path, kwargs))
        if method == "GET" and path == "/storage/v1/bucket/cocoaid-state":
            return httpx.Response(404, json={"message": "not found"})
        if method == "POST" and path == "/storage/v1/bucket":
            return httpx.Response(200, json={"name": "cocoaid-state"})
        raise AssertionError((method, path))

    monkeypatch.setattr(store, "_request", fake_request)
    assert store.ensure_bucket() is True
    creation = next(item for item in calls if item[0] == "POST")
    payload = creation[2]["json"]
    assert payload["id"] == "cocoaid-state"
    assert payload["public"] is False


def test_runtime_file_upload_and_lazy_restore(monkeypatch, tmp_path: Path) -> None:
    store = _configure_store(monkeypatch, tmp_path)
    payloads: dict[str, bytes] = {}

    def fake_request(method: str, path: str, **kwargs):
        if method == "GET" and path == "/storage/v1/bucket/cocoaid-state":
            return httpx.Response(200, json={"id": "cocoaid-state"})
        if method == "POST" and path == "/storage/v1/object/cocoaid-state/reports/report.pdf":
            payloads["report"] = kwargs["content"]
            return httpx.Response(200, json={"Key": "reports/report.pdf"})
        if method == "GET" and path == "/storage/v1/object/authenticated/cocoaid-state/reports/report.pdf":
            return httpx.Response(200, content=payloads["report"])
        raise AssertionError((method, path))

    monkeypatch.setattr(store, "_request", fake_request)
    source = tmp_path / "reports" / "report.pdf"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"%PDF-test")
    assert store.upload_runtime_file(source, namespace="reports") is True
    source.unlink()
    assert store.restore_runtime_file(source, namespace="reports") is True
    assert source.read_bytes() == b"%PDF-test"


def test_database_signature_tracks_wal_changes(monkeypatch, tmp_path: Path) -> None:
    store = _configure_store(monkeypatch, tmp_path)
    db = settings.database_path
    db.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE wal_sample (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
        conn.commit()
    first = store._db_signature(db)
    assert first is not None
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("INSERT INTO wal_sample(value) VALUES ('changed')")
        conn.commit()
        second = store._db_signature(db)
    assert second is not None
    assert second != first
