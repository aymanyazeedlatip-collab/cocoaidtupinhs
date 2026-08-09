from __future__ import annotations

import asyncio
import json
import platform
import socket
import ssl
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import httpx

from app.core.config import settings
from app.core.errors import CocoAidError
from app.schemas.weather import WeatherPointRequest
from app.weather.http import get_json
from app.weather.providers import fetch_point_forecast


def _print(title: str, value) -> None:
    print(f"{title}: {value}")


async def main() -> int:
    host = urlsplit(settings.open_meteo_base_url).hostname or "api.open-meteo.com"
    print("=" * 64)
    print("COCOAID WEATHER PROVIDER DIAGNOSTIC")
    print("=" * 64)
    _print("Python", sys.version.split()[0])
    _print("Platform", platform.platform())
    _print("HTTPX", httpx.__version__)
    _print("OpenSSL", ssl.OPENSSL_VERSION)
    _print("Provider", settings.open_meteo_base_url)
    _print("Connect timeout", settings.weather_connect_timeout_seconds)
    _print("Read timeout", settings.weather_read_timeout_seconds)
    _print("Attempts per mode", settings.weather_request_attempts)
    _print("Direct fallback", settings.weather_direct_connection_fallback)
    _print("System trust store", settings.weather_use_system_trust_store)

    try:
        addresses = sorted({item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)})
        _print("DNS addresses", ", ".join(addresses))
    except OSError as exc:
        print(f"DNS FAILED: {type(exc).__name__}: {str(exc).strip() or repr(exc)}")
        return 2

    try:
        payload = await get_json(
            settings.open_meteo_base_url,
            {
                "latitude": 6.334,
                "longitude": 124.952,
                "current": "temperature_2m",
                "forecast_days": 1,
                "timezone": "auto",
            },
        )
        if not isinstance(payload, dict) or "current" not in payload:
            print("MINIMAL REQUEST FAILED: provider returned an unexpected payload")
            return 3
        print("MINIMAL HTTPS REQUEST: PASSED")
    except CocoAidError as exc:
        print(f"MINIMAL HTTPS REQUEST FAILED: {exc.message}")
        print(json.dumps(exc.details, indent=2, ensure_ascii=False))
        return 4

    try:
        result = await fetch_point_forecast(
            WeatherPointRequest(
                latitude=6.334,
                longitude=124.952,
                model="auto",
                forecast_days=16,
                past_days=90,
            ),
            force_refresh=True,
        )
        count = len((result.get("hourly") or {}).get("time") or [])
        print(f"FULL 90-DAY + 16-DAY REQUEST: PASSED ({count} hourly timestamps)")
        print("WEATHER PROVIDER DIAGNOSTIC PASSED")
        return 0
    except CocoAidError as exc:
        print(f"FULL REQUEST FAILED: {exc.message}")
        print(json.dumps(exc.details, indent=2, ensure_ascii=False))
        return 5


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
