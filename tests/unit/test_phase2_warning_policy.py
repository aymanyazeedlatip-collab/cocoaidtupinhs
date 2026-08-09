from __future__ import annotations

from pathlib import Path


def test_starlette_testclient_deprecation_is_fixed_at_dependency_level_and_warnings_fail_tests():
    root = Path(__file__).resolve().parents[2]
    requirements = (root / "requirements.txt").read_text(encoding="utf-8")
    pytest_config = (root / "pytest.ini").read_text(encoding="utf-8")
    assert "httpx2>=2.9.1,<3" in requirements
    assert "filterwarnings = error" in pytest_config
    assert "ignore::" not in pytest_config
