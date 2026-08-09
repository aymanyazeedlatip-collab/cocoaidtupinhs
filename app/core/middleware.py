from __future__ import annotations

import contextvars
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.services.supabase_state import supabase_state

request_id_context: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)


def current_request_id() -> str | None:
    return request_id_context.get()


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a correlation ID and non-invasive request timing headers."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        incoming = request.headers.get(settings.request_id_header, "").strip()
        request_id = incoming[:128] if incoming else str(uuid.uuid4())
        token = request_id_context.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            request_id_context.reset(token)
        response.headers[settings.request_id_header] = request_id
        if settings.enable_request_metrics:
            response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.3f}"
        if request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"} and response.status_code < 500:
            # Render Free can disappear between requests. Wake the durable-state
            # sync promptly after successful mutations without blocking the HTTP
            # response on an external Supabase upload.
            supabase_state.request_sync()
        return response
