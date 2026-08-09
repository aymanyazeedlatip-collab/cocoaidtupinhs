from pathlib import Path


def test_windows_runner_isolates_external_pytest_plugins_and_each_test_file():
    root = Path(__file__).resolve().parents[2]
    batch = (root / "test.bat").read_text(encoding="utf-8")
    runner = (root / "scripts" / "run_test_suite.py").read_text(encoding="utf-8")
    assert 'set "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1"' in batch
    assert "python scripts\\run_test_suite.py" in batch
    assert '"pytest_asyncio.plugin"' in runner
    assert '"no:cacheprovider"' in runner
    assert "Every test file must be assigned exactly once" in runner
    assert "TEST FILE" in runner
    assert "fully isolated test-file processes" in runner
