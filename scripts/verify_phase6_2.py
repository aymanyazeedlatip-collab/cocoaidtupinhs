from __future__ import annotations

import os
import sys
from pathlib import Path

import lxml
import lxml.etree

from environment_paths import read_pointer

ROOT = Path(__file__).resolve().parents[1]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    setup_text = (ROOT / "setup.bat").read_text(encoding="utf-8").lower()
    _require("scripts\\environment_paths.py --ensure" in setup_text, "Path-safe environment setup is missing")
    _require("--only-binary=:all:" in setup_text, "Binary lxml wheel installation is missing")
    _require("-m venv .venv" not in setup_text, "Repository-local Windows .venv creation is still present")

    launchers = (
        "run.bat",
        "test.bat",
        "check_weather_provider.bat",
        "import_farmer_registry.bat",
        "rebuild_models.bat",
    )
    for launcher in launchers:
        text = (ROOT / launcher).read_text(encoding="utf-8").lower()
        _require(
            "scripts\\activate_environment.bat" in text,
            f"{launcher} does not use the shared environment resolver",
        )

    resource = (
        Path(lxml.__file__).resolve().parent
        / "isoschematron"
        / "resources"
        / "xsl"
        / "iso-schematron-xslt1"
        / "iso_schematron_skeleton_for_xslt1.xsl"
    )
    _require(resource.is_file(), f"Required lxml Schematron resource is missing: {resource}")
    _require(bool(lxml.etree.LXML_VERSION), "lxml runtime version was not resolved")

    if os.name == "nt":
        pointer = read_pointer(ROOT)
        _require(pointer is not None, "The COCOAID environment pointer was not created")
        _require(pointer.resolve() == Path(sys.prefix).resolve(), "Active Python does not match the recorded COCOAID environment")
        _require(ROOT.resolve() not in pointer.resolve().parents, "Windows environment must be outside the project tree")
        _require(len(str(resource)) < 260, f"lxml resource path is still too long ({len(str(resource))} characters)")

    print(
        {
            "lxml_version": ".".join(map(str, lxml.etree.LXML_VERSION)),
            "lxml_resource": str(resource),
            "resource_exists": resource.is_file(),
            "resource_path_length": len(str(resource)),
            "python_prefix": sys.prefix,
        }
    )
    print("PHASE 6.2 SETUP PATH VERIFICATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
