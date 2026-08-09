from __future__ import annotations

from pip._vendor.packaging.requirements import Requirement

from scripts.check_requirements_local import check


def test_local_requirement_checker_accepts_installed_package() -> None:
    ok, messages = check([Requirement("pip>=1")])
    assert ok is True
    assert any(message.startswith("OK pip ") for message in messages)


def test_local_requirement_checker_rejects_impossible_version_without_network() -> None:
    ok, messages = check([Requirement("pip==0.0.1")])
    assert ok is False
    assert any(message.startswith("MISMATCH pip:") for message in messages)


def test_setup_skips_network_when_environment_is_already_satisfied() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    setup = (root / "setup.bat").read_text(encoding="utf-8").lower()

    assert "scripts\\check_requirements_local.py --quiet" in setup
    assert "skipping pypi access and dependency installation" in setup
    assert "goto :dependencies_ready" in setup
    assert "pip check" in setup


def test_setup_does_not_upgrade_every_installed_package() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    setup = (root / "setup.bat").read_text(encoding="utf-8").lower()

    assert "pip install --upgrade pip setuptools wheel" not in setup
    assert "pip install --upgrade --prefer-binary -r requirements.txt" not in setup
    assert "--retries 1 --timeout 8 --prefer-binary -r requirements.txt" in setup
    assert "--retries 1 --timeout 8 --only-binary=:all:" in setup
