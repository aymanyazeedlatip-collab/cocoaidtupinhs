# Starlette TestClient Warning Fix

The Phase 1 Windows test warning was caused by newer Starlette versions deprecating plain `httpx` for `starlette.testclient`.

Phase 2 fixes this at the dependency level by installing `httpx2>=2.9.1,<3`. `setup.bat` verifies that `httpx2` imports successfully. Pytest is configured with `filterwarnings = error`, so any future warning fails the test suite instead of being hidden.

The tests themselves continue to import `TestClient` from FastAPI/Starlette, which selects the supported transport runtime.
