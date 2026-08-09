from __future__ import annotations

import asyncio
import logging
import ssl
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.core.config import settings
from app.core.errors import ProviderRateLimitError, ProviderUnavailableError

logger = logging.getLogger(__name__)

_DEFAULT_HEADERS = {
    "User-Agent": "COCOAID/3.0 educational-research-prototype",
    "Accept": "application/json",
}
_RETRIABLE_STATUS_CODES = {500, 502, 503, 504}


@dataclass(frozen=True)
class _AttemptFailure:
    mode: str
    attempt: int
    exception_type: str
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "attempt": self.attempt,
            "exception_type": self.exception_type,
            "message": self.message,
        }


def _exception_message(exc: BaseException) -> str:
    """Return a useful message even for HTTPX exceptions whose ``str`` is blank."""
    parts: list[str] = []
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        text = str(current).strip()
        if text:
            parts.append(text)
        current = current.__cause__ or current.__context__
    if parts:
        return " | caused by: ".join(dict.fromkeys(parts))
    representation = repr(exc).strip()
    return representation if representation else "No exception message was supplied by the network stack"


def _system_ssl_context() -> ssl.SSLContext | bool:
    """Use the operating-system trust store when available.

    On Windows this permits HTTPS inspection products and institution-managed
    certificates to work without disabling TLS verification. The fallback remains
    HTTPX's normal verified CA configuration.
    """
    if not settings.weather_use_system_trust_store:
        return True
    try:
        import truststore

        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except (ImportError, OSError, RuntimeError):
        logger.warning("System TLS trust store unavailable; using HTTPX default CA bundle")
        return True


def _timeout() -> httpx.Timeout:
    return httpx.Timeout(
        timeout=settings.weather_read_timeout_seconds,
        connect=settings.weather_connect_timeout_seconds,
        read=settings.weather_read_timeout_seconds,
        write=settings.weather_read_timeout_seconds,
        pool=settings.weather_connect_timeout_seconds,
    )


def _safe_provider_details(url: str, failures: list[_AttemptFailure]) -> dict[str, Any]:
    parsed = urlsplit(url)
    return {
        "provider_host": parsed.hostname or "unknown",
        "provider_scheme": parsed.scheme,
        "connect_timeout_seconds": settings.weather_connect_timeout_seconds,
        "read_timeout_seconds": settings.weather_read_timeout_seconds,
        "direct_fallback_enabled": settings.weather_direct_connection_fallback,
        "attempts": [failure.as_dict() for failure in failures],
        "troubleshooting": [
            "Confirm that the computer can open https://api.open-meteo.com in a browser.",
            "Temporarily disable a VPN only if local policy permits, then retry.",
            "Check whether antivirus or a school/company proxy is inspecting HTTPS traffic.",
            "Run check_weather_provider.bat from the project folder for a focused diagnostic.",
        ],
    }


async def _request(
    url: str,
    *,
    params: dict | None,
    headers: dict[str, str],
    accept_json: bool,
) -> httpx.Response:
    failures: list[_AttemptFailure] = []
    modes: list[tuple[str, bool]] = [("environment", True)]
    if settings.weather_direct_connection_fallback:
        modes.append(("direct", False))

    attempts_per_mode = max(1, settings.weather_request_attempts)
    for mode_name, trust_env in modes:
        for attempt in range(1, attempts_per_mode + 1):
            try:
                ssl_context = _system_ssl_context()
                transport = httpx.AsyncHTTPTransport(
                    retries=1,
                    verify=ssl_context,
                    trust_env=trust_env,
                )
                async with httpx.AsyncClient(
                    timeout=_timeout(),
                    follow_redirects=True,
                    headers=headers,
                    trust_env=trust_env,
                    transport=transport,
                ) as client:
                    response = await client.get(url, params=params)

                if response.status_code == 429:
                    raise ProviderRateLimitError(
                        "Weather provider rate limit reached",
                        details={
                            "provider_host": urlsplit(url).hostname,
                            "retry_after": response.headers.get("Retry-After"),
                        },
                    )

                if response.status_code in _RETRIABLE_STATUS_CODES:
                    body = response.text.strip()[:300]
                    failures.append(
                        _AttemptFailure(
                            mode=mode_name,
                            attempt=attempt,
                            exception_type=f"HTTP_{response.status_code}",
                            message=body or response.reason_phrase or "Temporary provider error",
                        )
                    )
                    if attempt < attempts_per_mode:
                        await asyncio.sleep(0.4 * attempt)
                        continue
                    break

                if response.status_code >= 400:
                    detail = response.text.strip()[:500]
                    if accept_json:
                        try:
                            payload = response.json()
                            if isinstance(payload, dict):
                                detail = str(payload.get("reason") or payload.get("error") or detail)
                        except ValueError:
                            pass
                    raise ProviderUnavailableError(
                        f"Weather provider returned HTTP {response.status_code}: "
                        f"{detail or response.reason_phrase or 'request rejected'}",
                        details={
                            "provider_host": urlsplit(url).hostname,
                            "http_status": response.status_code,
                            "network_mode": mode_name,
                        },
                    )
                return response
            except ProviderRateLimitError:
                raise
            except ProviderUnavailableError:
                raise
            except httpx.RequestError as exc:
                failure = _AttemptFailure(
                    mode=mode_name,
                    attempt=attempt,
                    exception_type=type(exc).__name__,
                    message=_exception_message(exc),
                )
                failures.append(failure)
                logger.warning(
                    "Weather provider attempt failed mode=%s attempt=%s type=%s message=%s",
                    mode_name,
                    attempt,
                    failure.exception_type,
                    failure.message,
                )
                if attempt < attempts_per_mode:
                    await asyncio.sleep(0.4 * attempt)

    final = failures[-1] if failures else _AttemptFailure(
        mode="unknown", attempt=0, exception_type="UnknownNetworkError", message="No provider response"
    )
    raise ProviderUnavailableError(
        f"Weather provider connection failed after {len(failures)} attempt(s): "
        f"{final.exception_type}: {final.message}",
        details=_safe_provider_details(url, failures),
    )


async def get_json(url: str, params: dict | None = None) -> dict | list:
    response = await _request(url, params=params, headers=_DEFAULT_HEADERS, accept_json=True)
    try:
        return response.json()
    except ValueError as exc:
        raise ProviderUnavailableError(
            "Weather provider returned invalid JSON",
            details={
                "provider_host": urlsplit(url).hostname,
                "content_type": response.headers.get("content-type"),
                "response_preview": response.text[:300],
            },
        ) from exc


async def get_text(url: str, params: dict | None = None) -> str:
    headers = {
        "User-Agent": _DEFAULT_HEADERS["User-Agent"],
        "Accept": "application/xml,text/xml,*/*",
    }
    response = await _request(url, params=params, headers=headers, accept_json=False)
    return response.text
