from __future__ import annotations

import logging
import os
import sqlite3
import tempfile
import threading
import time
from pathlib import Path
from contextlib import closing
from typing import Any
from urllib.parse import quote

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class SupabaseStateStore:
    """Durable state bridge for Render Free deployments.

    COCOAID keeps its battle-tested SQLite repositories locally. On ephemeral hosts,
    this bridge restores the latest consistent SQLite snapshot from a private
    Supabase Storage bucket at startup and periodically uploads a new snapshot when
    the database changes. Generated reports and assistant document extracts are
    stored as individual private objects so they can be restored lazily after a
    cold start.

    This intentionally avoids exposing Supabase credentials to the browser and
    avoids a risky wholesale rewrite of the research repositories to another SQL
    dialect solely for hosting.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread: threading.Thread | None = None
        self._bucket_ready = False
        self._last_db_signature: tuple[int, int, int, int] | None = None
        self._last_sync_at: float | None = None
        self._last_error: str | None = None

    @property
    def configured(self) -> bool:
        return bool(
            settings.supabase_state_sync_enabled
            and settings.supabase_url
            and settings.supabase_secret_key
            and settings.supabase_storage_bucket
        )

    @property
    def required(self) -> bool:
        return bool(settings.supabase_state_required)

    def _headers(self, *, content_type: str | None = None, upsert: bool = False) -> dict[str, str]:
        key = str(settings.supabase_secret_key or "").strip()
        headers = {
            "apikey": key,
            "User-Agent": "COCOAID-Server/1.0",
        }
        # Legacy service_role keys are JWTs and Storage accepts them as a bearer
        # token. New sb_secret_* keys are opaque server keys and should be sent as
        # an apikey instead of being treated as a JWT.
        if key and not key.startswith("sb_secret_"):
            headers["Authorization"] = f"Bearer {key}"
        if content_type:
            headers["Content-Type"] = content_type
        if upsert:
            headers["x-upsert"] = "true"
        return headers

    def _url(self, path: str) -> str:
        base = str(settings.supabase_url or "").strip().rstrip("/")
        return f"{base}{path}"

    def _timeout(self) -> httpx.Timeout:
        seconds = float(settings.supabase_state_timeout_seconds)
        return httpx.Timeout(seconds, connect=min(seconds, 10.0))

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        return httpx.request(method, self._url(path), timeout=self._timeout(), follow_redirects=True, **kwargs)

    def validate_configuration(self) -> None:
        if not settings.supabase_state_sync_enabled:
            if self.required:
                raise RuntimeError("SUPABASE_STATE_REQUIRED=true but SUPABASE_STATE_SYNC_ENABLED is disabled.")
            return
        missing: list[str] = []
        if not settings.supabase_url:
            missing.append("SUPABASE_URL")
        if not settings.supabase_secret_key:
            missing.append("SUPABASE_SECRET_KEY")
        if not settings.supabase_storage_bucket:
            missing.append("SUPABASE_STORAGE_BUCKET")
        if missing and self.required:
            raise RuntimeError(
                "COCOAID durable state is required but these Render environment variables are missing: "
                + ", ".join(missing)
            )
        if settings.supabase_url and not str(settings.supabase_url).startswith("https://"):
            raise RuntimeError("SUPABASE_URL must use https://")

    def ensure_bucket(self) -> bool:
        if not self.configured:
            return False
        with self._lock:
            if self._bucket_ready:
                return True
            bucket = quote(str(settings.supabase_storage_bucket), safe="")
            response = self._request(
                "GET",
                f"/storage/v1/bucket/{bucket}",
                headers=self._headers(),
            )
            if response.status_code == 200:
                self._bucket_ready = True
                self._last_error = None
                return True
            if response.status_code != 404:
                self._last_error = f"Supabase bucket check failed ({response.status_code}): {response.text[:240]}"
                if self.required:
                    raise RuntimeError(self._last_error)
                logger.warning(self._last_error)
                return False

            payload = {
                "id": settings.supabase_storage_bucket,
                "name": settings.supabase_storage_bucket,
                "public": False,
                "file_size_limit": int(settings.supabase_state_max_object_bytes),
            }
            response = self._request(
                "POST",
                "/storage/v1/bucket",
                headers=self._headers(content_type="application/json"),
                json=payload,
            )
            if response.status_code not in {200, 201}:
                # Concurrent first starts can race to create the bucket. Recheck
                # before declaring a failure.
                recheck = self._request(
                    "GET",
                    f"/storage/v1/bucket/{bucket}",
                    headers=self._headers(),
                )
                if recheck.status_code != 200:
                    self._last_error = f"Supabase bucket creation failed ({response.status_code}): {response.text[:240]}"
                    if self.required:
                        raise RuntimeError(self._last_error)
                    logger.warning(self._last_error)
                    return False
            self._bucket_ready = True
            self._last_error = None
            logger.info("Supabase durable-state bucket is ready: %s", settings.supabase_storage_bucket)
            return True

    def _object_path(self, object_name: str) -> str:
        bucket = quote(str(settings.supabase_storage_bucket), safe="")
        object_key = quote(object_name.strip("/"), safe="/")
        return f"{bucket}/{object_key}"

    def upload_bytes(self, object_name: str, payload: bytes, *, content_type: str) -> bool:
        if not self.configured or not self.ensure_bucket():
            return False
        if len(payload) > int(settings.supabase_state_max_object_bytes):
            message = (
                f"Refusing to upload {object_name}: {len(payload)} bytes exceeds configured "
                f"Supabase object limit of {settings.supabase_state_max_object_bytes} bytes."
            )
            self._last_error = message
            if self.required:
                raise RuntimeError(message)
            logger.error(message)
            return False
        with self._lock:
            response = self._request(
                "POST",
                f"/storage/v1/object/{self._object_path(object_name)}",
                headers=self._headers(content_type=content_type, upsert=True),
                content=payload,
            )
            if response.status_code not in {200, 201}:
                self._last_error = f"Supabase upload failed for {object_name} ({response.status_code}): {response.text[:240]}"
                if self.required:
                    raise RuntimeError(self._last_error)
                logger.warning(self._last_error)
                return False
            self._last_error = None
            return True

    def download_bytes(self, object_name: str) -> bytes | None:
        if not self.configured or not self.ensure_bucket():
            return None
        with self._lock:
            response = self._request(
                "GET",
                f"/storage/v1/object/authenticated/{self._object_path(object_name)}",
                headers=self._headers(),
            )
            if response.status_code == 404:
                return None
            if response.status_code != 200:
                self._last_error = f"Supabase download failed for {object_name} ({response.status_code}): {response.text[:240]}"
                if self.required:
                    raise RuntimeError(self._last_error)
                logger.warning(self._last_error)
                return None
            self._last_error = None
            return response.content

    @staticmethod
    def _db_signature(path: Path) -> tuple[int, int, int, int] | None:
        try:
            stat = path.stat()
        except FileNotFoundError:
            return None
        wal = Path(str(path) + "-wal")
        try:
            wal_stat = wal.stat()
            wal_mtime = wal_stat.st_mtime_ns
            wal_size = wal_stat.st_size
        except FileNotFoundError:
            wal_mtime = 0
            wal_size = 0
        return (stat.st_mtime_ns, stat.st_size, wal_mtime, wal_size)

    @staticmethod
    def _validate_sqlite(path: Path) -> None:
        with closing(sqlite3.connect(path, timeout=30)) as conn:
            result = conn.execute("PRAGMA quick_check").fetchone()
        if not result or str(result[0]).lower() != "ok":
            raise RuntimeError("Downloaded Supabase database snapshot failed SQLite quick_check.")

    def restore_database(self) -> bool:
        """Restore the latest remote SQLite state before local migrations run."""
        if not self.configured:
            return False
        payload = self.download_bytes(settings.supabase_state_object)
        if payload is None:
            logger.info("No remote COCOAID database snapshot exists yet; first-deploy initialization will create one.")
            return False
        if len(payload) > int(settings.supabase_state_max_object_bytes):
            raise RuntimeError("Remote COCOAID database snapshot exceeds the configured safe object size.")
        destination = settings.database_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix="cocoaid_restore_", suffix=".sqlite3", delete=False, dir=destination.parent) as temp:
            temp_path = Path(temp.name)
            temp.write(payload)
        try:
            self._validate_sqlite(temp_path)
            os.replace(temp_path, destination)
        finally:
            temp_path.unlink(missing_ok=True)
        self._last_db_signature = self._db_signature(destination)
        self._last_sync_at = time.time()
        logger.info("Restored COCOAID SQLite state from Supabase Storage (%d bytes).", len(payload))
        return True

    def _database_snapshot_bytes(self) -> bytes:
        source = settings.database_path
        if not source.exists():
            return b""
        source.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix="cocoaid_snapshot_", suffix=".sqlite3")
        os.close(fd)
        temp_path = Path(temp_name)
        try:
            with closing(sqlite3.connect(source, timeout=30)) as src, closing(sqlite3.connect(temp_path, timeout=30)) as dst:
                src.backup(dst)
            self._validate_sqlite(temp_path)
            return temp_path.read_bytes()
        finally:
            temp_path.unlink(missing_ok=True)

    def sync_database(self, *, force: bool = False) -> bool:
        if not self.configured:
            return False
        signature = self._db_signature(settings.database_path)
        if signature is None:
            return False
        if not force and signature == self._last_db_signature:
            return False
        with self._lock:
            # Recheck after acquiring the lock so concurrent triggers do not upload
            # the same snapshot twice.
            signature = self._db_signature(settings.database_path)
            if signature is None:
                return False
            if not force and signature == self._last_db_signature:
                return False
            payload = self._database_snapshot_bytes()
            if not payload:
                return False
            if self.upload_bytes(
                settings.supabase_state_object,
                payload,
                content_type="application/vnd.sqlite3",
            ):
                self._last_db_signature = self._db_signature(settings.database_path)
                self._last_sync_at = time.time()
                logger.info("Synced COCOAID SQLite state to Supabase Storage (%d bytes).", len(payload))
                return True
            return False

    def upload_runtime_file(self, local_path: Path, *, namespace: str) -> bool:
        if not self.configured or not local_path.exists() or not local_path.is_file():
            return False
        object_name = f"{namespace.strip('/')}/{local_path.name}"
        suffix = local_path.suffix.lower()
        content_type = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".txt": "text/plain; charset=utf-8",
            ".json": "application/json",
        }.get(suffix, "application/octet-stream")
        return self.upload_bytes(object_name, local_path.read_bytes(), content_type=content_type)

    def restore_runtime_file(self, local_path: Path, *, namespace: str) -> bool:
        if local_path.exists():
            return True
        object_name = f"{namespace.strip('/')}/{local_path.name}"
        payload = self.download_bytes(object_name)
        if payload is None:
            return False
        local_path.parent.mkdir(parents=True, exist_ok=True)
        temp = local_path.with_name(local_path.name + ".remote.tmp")
        temp.write_bytes(payload)
        os.replace(temp, local_path)
        return True

    def request_sync(self) -> None:
        """Wake the background sync after a successful mutating API request."""
        if self.configured:
            self._wake.set()

    def start_background_sync(self) -> None:
        if not self.configured or self._thread is not None:
            return
        self._stop.clear()
        self._wake.clear()

        def loop() -> None:
            while not self._stop.is_set():
                # Wake immediately after writes, with a periodic timeout as a
                # safety net for background jobs that modify SQLite directly.
                self._wake.wait(float(settings.supabase_state_sync_seconds))
                self._wake.clear()
                if self._stop.is_set():
                    break
                try:
                    self.sync_database()
                except Exception as exc:  # pragma: no cover - network resilience path
                    self._last_error = str(exc)
                    logger.warning("Supabase state sync attempt failed: %s", exc)

        self._thread = threading.Thread(target=loop, daemon=True, name="cocoaid-supabase-state-sync")
        self._thread.start()

    def stop_background_sync(self) -> None:
        self._stop.set()
        self._wake.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=3.0)
        self._thread = None
        if self.configured:
            try:
                self.sync_database(force=True)
            except Exception as exc:  # pragma: no cover - shutdown best effort
                logger.warning("Final Supabase state sync failed during shutdown: %s", exc)

    def status(self) -> dict[str, Any]:
        return {
            "enabled": bool(settings.supabase_state_sync_enabled),
            "configured": self.configured,
            "required": self.required,
            "bucket": settings.supabase_storage_bucket if self.configured else None,
            "database_object": settings.supabase_state_object if self.configured else None,
            "sync_seconds": settings.supabase_state_sync_seconds,
            "last_sync_at_epoch": self._last_sync_at,
            "last_error": self._last_error,
        }


supabase_state = SupabaseStateStore()
