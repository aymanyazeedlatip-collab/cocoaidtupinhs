# Weather Provider Resilience Hotfix 1.0.1

This hotfix addresses blank `503 provider_unavailable` responses from
`POST /api/v2/weather/assimilate` when the underlying HTTP client cannot reach
Open-Meteo.

## Changes

- Increased weather-specific read timeout to 60 seconds and connect timeout to 20 seconds.
- Added verified TLS support through the operating-system certificate store using `truststore`.
- Added retry handling for connection failures and temporary HTTP 500/502/503/504 responses.
- Added a direct-connection fallback that ignores broken proxy environment variables after the normal environment-aware request fails.
- Preserved TLS certificate verification; the hotfix never uses `verify=False`.
- Replaced blank network errors with exception type, nested cause, provider host, attempt history, timeout values, and troubleshooting guidance.
- Added `check_weather_provider.bat` for DNS, minimal HTTPS, and full assimilation diagnostics.
- Added automated regression coverage for blank HTTPX errors and proxy-bypass fallback.

## Compatibility

No database migration is required. The API contract remains
`3.0.0-draft.6`. The weather engine reports `1.0.1` and the provider hotfix
identifier `weather-provider-resilience-1.0.1`.

## Validation

- 214 automated tests passed across all 63 test files.
- Phase 0 through Phase 6 verification scripts passed.
- Python compilation and both JavaScript syntax checks passed.
- The build environment had no outbound DNS, so the live Open-Meteo request must be confirmed on the user's internet-connected Windows computer.
