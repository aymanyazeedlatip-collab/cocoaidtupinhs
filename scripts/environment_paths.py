from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ENV_POINTER_FILENAME = ".cocoaid_venv_path"
ENV_RELEASE_KEY = "phase11"


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def select_environment_path(
    *,
    project: Path | None = None,
    platform: str | None = None,
    environ: dict[str, str] | None = None,
    python_version: tuple[int, int] | None = None,
) -> Path:
    """Return a short, stable virtual-environment path.

    On Windows the environment deliberately lives outside the extracted project so
    deep packages such as lxml cannot exceed the legacy MAX_PATH limit even when
    the project itself is inside several nested folders.
    """

    project = (project or project_root()).resolve()
    platform = platform or sys.platform
    environ = dict(os.environ if environ is None else environ)
    python_version = python_version or (sys.version_info.major, sys.version_info.minor)

    override = environ.get("COCOAID_VENV_DIR", "").strip()
    if override:
        expanded = Path(os.path.expandvars(os.path.expanduser(override)))
        return expanded if platform.startswith("win") else expanded.resolve()

    py_key = f"py{python_version[0]}{python_version[1]}"
    if platform.startswith("win"):
        base = environ.get("LOCALAPPDATA", "").strip()
        if not base:
            user_profile = environ.get("USERPROFILE", "").strip()
            if user_profile:
                base = str(Path(user_profile) / "AppData" / "Local")
            else:
                base = str(Path.home() / "AppData" / "Local")
        return Path(base) / "COCOAID" / "venvs" / f"{ENV_RELEASE_KEY}_{py_key}"

    # Non-Windows development environments can safely use a repository-local path.
    return (project / ".venv").resolve()


def pointer_path(project: Path | None = None) -> Path:
    return (project or project_root()) / ENV_POINTER_FILENAME


def write_pointer(environment_path: Path, project: Path | None = None) -> Path:
    pointer = pointer_path(project)
    pointer.write_text(str(environment_path.resolve()) + "\n", encoding="utf-8")
    return pointer


def read_pointer(project: Path | None = None) -> Path | None:
    pointer = pointer_path(project)
    if not pointer.exists():
        return None
    value = pointer.read_text(encoding="utf-8").strip()
    return Path(value) if value else None


def environment_python(environment_path: Path) -> Path:
    if sys.platform.startswith("win"):
        return environment_path / "Scripts" / "python.exe"
    return environment_path / "bin" / "python"


def _environment_is_usable(environment_path: Path) -> bool:
    python = environment_python(environment_path)
    if not python.is_file():
        return False
    result = subprocess.run(
        [str(python), "-c", "import sys; print(sys.executable)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def ensure_environment(environment_path: Path, base_python: str) -> None:
    environment_path.parent.mkdir(parents=True, exist_ok=True)
    if environment_path.exists() and not _environment_is_usable(environment_path):
        shutil.rmtree(environment_path, ignore_errors=True)
    if not environment_path.exists():
        subprocess.run(
            [base_python, "-m", "venv", str(environment_path)],
            check=True,
        )
    if not _environment_is_usable(environment_path):
        raise RuntimeError(f"Virtual environment is not usable: {environment_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve the COCOAID virtual environment")
    parser.add_argument("--ensure", action="store_true", help="create or repair the environment")
    parser.add_argument("--base-python", default=sys.executable)
    parser.add_argument("--path-only", action="store_true")
    args = parser.parse_args()

    environment_path = select_environment_path()
    if args.ensure:
        ensure_environment(environment_path, args.base_python)
        write_pointer(environment_path)
    if args.path_only:
        print(environment_path)
    else:
        print(f"COCOAID environment: {environment_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
