from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.core.config import settings
from app.core.errors import CocoAidError, ErrorCode, ProviderRateLimitError
from app.core.middleware import current_request_id


_JSON_COMMON_CAUSES = [
    "A missing comma between two fields or list items",
    "A UUID or other text value pasted without double quotes",
    "Smart quotes copied from a formatted document instead of plain double quotes",
    "A trailing comma before a closing brace or bracket",
    "Extra text pasted before or after the JSON object",
]


def _json_position(body: str, offset: int) -> tuple[int, int]:
    safe_offset = max(0, min(offset, len(body)))
    line = body.count("\n", 0, safe_offset) + 1
    last_newline = body.rfind("\n", 0, safe_offset)
    column = safe_offset + 1 if last_newline < 0 else safe_offset - last_newline
    return line, column


def _format_validation_error(exc: RequestValidationError | ValidationError) -> tuple[str, list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    messages: list[str] = []
    for item in exc.errors():
        location = [str(part) for part in item.get("loc", []) if part not in {"body"}]
        field = ".".join(location) or "request"
        message = str(item.get("msg", "Invalid value"))
        value = item.get("input")
        errors.append({"field": field, "message": message, "value": value})
        messages.append(f"{field}: {message}")
    summary = "Invalid request data. " + "; ".join(messages[:6])
    if len(messages) > 6:
        summary += f"; and {len(messages) - 6} more validation error(s)"
    return summary, errors


async def _format_request_validation_error(
    request: Request,
    exc: RequestValidationError,
) -> tuple[str, list[dict[str, Any]], dict[str, Any] | None]:
    raw_errors = exc.errors()
    json_error = next((item for item in raw_errors if item.get("type") == "json_invalid"), None)
    if not json_error:
        detail, errors = _format_validation_error(exc)
        return detail, errors, None

    location = list(json_error.get("loc", []))
    offset = next((part for part in reversed(location) if isinstance(part, int)), 0)
    parser_message = str(json_error.get("ctx", {}).get("error") or "Malformed JSON")
    try:
        body = (await request.body()).decode("utf-8", errors="replace")
    except Exception:
        body = ""
    line, column = _json_position(body, int(offset))

    user_message = (
        f"Malformed JSON at line {line}, column {column}: {parser_message}. "
        "The request was not processed. Use plain double quotes and verify commas around the indicated position."
    )
    normalized_error = {
        "field": "request_body",
        "message": user_message,
        "value": None,
        "line": line,
        "column": column,
        "character_offset": int(offset),
        "parser_message": parser_message,
    }
    diagnostic = {
        "line": line,
        "column": column,
        "character_offset": int(offset),
        "parser_message": parser_message,
        "common_causes": _JSON_COMMON_CAUSES,
        "body_echoed": False,
        "recovery": (
            "Use the Phase 8 resume workflow script or paste the corrected JSON template exactly, "
            "then replace only the quoted UUID placeholders."
        ),
    }
    return user_message, [normalized_error], diagnostic


def _problem_payload(
    request: Request,
    *,
    status: int,
    code: str,
    detail: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    # ``detail`` remains at the top level for legacy frontend compatibility.
    return {
        "detail": detail,
        "code": code,
        "status": status,
        "path": request.url.path,
        "request_id": current_request_id(),
        "details": details or {},
    }


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        detail, errors, json_error = await _format_request_validation_error(request, exc)
        details: dict[str, Any] = {"errors": errors}
        if json_error:
            details["json_error"] = json_error
        payload = _problem_payload(
            request,
            status=422,
            code=ErrorCode.VALIDATION_ERROR,
            detail=detail,
            details=details,
        )
        # Legacy clients read the top-level errors array.
        payload["errors"] = errors
        return JSONResponse(status_code=422, content=payload)

    @app.exception_handler(ValidationError)
    async def contract_validation_error_handler(request: Request, exc: ValidationError):
        detail, errors = _format_validation_error(exc)
        payload = _problem_payload(
            request,
            status=422,
            code=ErrorCode.VALIDATION_ERROR,
            detail=detail,
            details={"errors": errors},
        )
        payload["errors"] = errors
        return JSONResponse(status_code=422, content=payload)

    @app.exception_handler(CocoAidError)
    async def application_error_handler(request: Request, exc: CocoAidError):
        payload = _problem_payload(
            request,
            status=exc.status_code,
            code=str(exc.error_code),
            detail=exc.message,
            details=exc.details,
        )
        if exc.status_code in {429, 503}:
            payload["provider_error"] = True
            payload["offline_mode"] = settings.offline_mode
        headers = None
        if isinstance(exc, ProviderRateLimitError):
            headers = {"Retry-After": str(settings.provider_cooldown_seconds)}
        return JSONResponse(status_code=exc.status_code, content=payload, headers=headers)
