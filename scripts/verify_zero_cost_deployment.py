from __future__ import annotations

import json
import sqlite3
import tempfile
import sys
from contextlib import closing
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check_blueprint() -> None:
    text = (ROOT / "render.yaml").read_text(encoding="utf-8")
    assert "type: web" in text
    assert "name: cocoaid-backend-free" in text
    assert "plan: free" in text, "Render backend must stay on the Free instance type"
    assert "plan: standard" not in text
    assert "\n    disk:" not in text and "\n      disk:" not in text, "A Render disk would require a paid service"
    assert "maxShutdownDelaySeconds" not in text
    assert "numInstances: 1" in text
    for required in (
        "SUPABASE_URL", "SUPABASE_SECRET_KEY", "SUPABASE_STATE_SYNC_ENABLED",
        "SUPABASE_STATE_REQUIRED", "SUPABASE_STORAGE_BUCKET", "PERSISTENT_DATA_DIR",
        "AUTO_PHASE_WORKFLOWS",
    ):
        assert f"key: {required}" in text, f"Missing Render environment declaration: {required}"
    assert "value: /tmp/cocoaid-runtime" in text
    # Both server secrets must be supplied from the Render dashboard/Blueprint
    # form rather than committed to Git.
    url_block = text.split("key: SUPABASE_URL", 1)[1].split("- key:", 1)[0]
    key_block = text.split("key: SUPABASE_SECRET_KEY", 1)[1].split("- key:", 1)[0]
    assert "sync: false" in url_block
    assert "sync: false" in key_block


def check_vercel() -> None:
    text = (ROOT / "vercel.mjs").read_text(encoding="utf-8")
    assert "COCOAID_BACKEND_URL" in text
    assert "/api/:path*" in text
    assert "vercel_dist" in text


def check_remote_state_round_trip() -> None:
    from app.core.config import settings
    from app.services.supabase_state import SupabaseStateStore

    original = {
        name: getattr(settings, name)
        for name in (
            "supabase_state_sync_enabled", "supabase_state_required", "supabase_url",
            "supabase_secret_key", "supabase_storage_bucket", "supabase_state_object",
            "supabase_state_max_object_bytes", "database_path",
        )
    }
    try:
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            settings.supabase_state_sync_enabled = True
            settings.supabase_state_required = True
            settings.supabase_url = "https://verify.supabase.co"
            settings.supabase_secret_key = "sb_secret_verifier"
            settings.supabase_storage_bucket = "cocoaid-state"
            settings.supabase_state_object = "state/coco_aid.sqlite3"
            settings.supabase_state_max_object_bytes = 48 * 1024 * 1024
            settings.database_path = folder / "coco_aid.sqlite3"

            store = SupabaseStateStore()
            objects: dict[str, bytes] = {}
            bucket_exists = False

            def fake_request(method: str, path: str, **kwargs):
                nonlocal bucket_exists
                if path == "/storage/v1/bucket/cocoaid-state" and method == "GET":
                    return httpx.Response(200 if bucket_exists else 404, json={"id": "cocoaid-state"})
                if path == "/storage/v1/bucket" and method == "POST":
                    bucket_exists = True
                    return httpx.Response(200, json={"name": "cocoaid-state"})
                prefix = "/storage/v1/object/cocoaid-state/"
                auth_prefix = "/storage/v1/object/authenticated/cocoaid-state/"
                if method == "POST" and path.startswith(prefix):
                    objects[path.removeprefix(prefix)] = bytes(kwargs.get("content") or b"")
                    return httpx.Response(200, json={"Key": path.removeprefix(prefix)})
                if method == "GET" and path.startswith(auth_prefix):
                    key = path.removeprefix(auth_prefix)
                    data = objects.get(key)
                    return httpx.Response(200, content=data) if data is not None else httpx.Response(404)
                raise AssertionError(f"Unexpected fake Supabase request: {method} {path}")

            store._request = fake_request  # type: ignore[method-assign]
            assert store.ensure_bucket() is True
            settings.database_path.parent.mkdir(parents=True, exist_ok=True)
            with closing(sqlite3.connect(settings.database_path)) as conn:
                conn.execute("CREATE TABLE verifier (id INTEGER PRIMARY KEY, payload TEXT NOT NULL)")
                conn.execute("INSERT INTO verifier(payload) VALUES ('zero-cost-state')")
                conn.commit()
            assert store.sync_database(force=True) is True
            assert "state/coco_aid.sqlite3" in objects
            settings.database_path.unlink()
            assert store.restore_database() is True
            with closing(sqlite3.connect(settings.database_path)) as conn:
                assert conn.execute("SELECT payload FROM verifier").fetchone()[0] == "zero-cost-state"
    finally:
        for name, value in original.items():
            setattr(settings, name, value)


def main() -> int:
    check_blueprint()
    check_vercel()
    check_remote_state_round_trip()
    print(json.dumps({
        "status": "passed",
        "render_plan": "free",
        "render_disk": False,
        "supabase_state_round_trip": True,
        "manual_phase_ids_required": False,
    }, indent=2))
    print("ZERO-COST DEPLOYMENT VERIFICATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
