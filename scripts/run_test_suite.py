from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"


def _relative(paths: list[Path]) -> list[str]:
    return [path.relative_to(ROOT).as_posix() for path in paths]


def _test_files() -> list[Path]:
    files = sorted(TESTS.rglob("test_*.py"))
    if not files:
        raise RuntimeError("No COCOAID test files were discovered")
    if len(files) != len(set(files)):
        raise RuntimeError("Every test file must be assigned exactly once")
    return files


def _junit_count(path: Path) -> int:
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    tests = sum(int(suite.attrib.get("tests", 0)) for suite in suites)
    failures = sum(int(suite.attrib.get("failures", 0)) for suite in suites)
    errors = sum(int(suite.attrib.get("errors", 0)) for suite in suites)
    skipped = sum(int(suite.attrib.get("skipped", 0)) for suite in suites)
    if failures or errors:
        raise RuntimeError(
            f"JUnit verification found failures={failures}, errors={errors}, skipped={skipped}"
        )
    return tests


def _run_file(number: int, total_files: int, path: Path, env: dict[str, str], report: Path) -> int:
    relative = _relative([path])[0]
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-p",
        "pytest_asyncio.plugin",
        "-p",
        "no:cacheprovider",
        "-q",
        f"--junitxml={report}",
        relative,
    ]
    print(f"\n=== COCOAID TEST FILE {number}/{total_files}: {relative} ===", flush=True)
    result = subprocess.run(command, cwd=ROOT, env=env)
    if result.returncode != 0:
        raise SystemExit(result.returncode)
    if not report.exists():
        raise RuntimeError(f"Test file {relative} did not produce its JUnit verification report")
    return _junit_count(report)


def main() -> int:
    files = _test_files()
    env = os.environ.copy()
    env.update({
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "VECLIB_MAXIMUM_THREADS": "1",
    })
    total = 0
    with tempfile.TemporaryDirectory(prefix="cocoaid-tests-") as temporary:
        folder = Path(temporary)
        for index, path in enumerate(files, start=1):
            total += _run_file(index, len(files), path, env, folder / f"test-file-{index}.xml")
    print(
        f"\nALL COCOAID TESTS PASSED: {total} tests across "
        f"{len(files)} fully isolated test-file processes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
