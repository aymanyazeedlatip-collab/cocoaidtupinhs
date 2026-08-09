from __future__ import annotations

from pathlib import Path

from scripts.environment_paths import select_environment_path

ROOT = Path(__file__).resolve().parents[2]


def test_windows_environment_is_outside_deep_project_and_short() -> None:
    project = Path("C:/Users/Lenovo/Desktop/PROJECTS/COCOAID/NEW PROJECT/") / ("nested-" * 20)
    path = select_environment_path(
        project=project,
        platform="win32",
        environ={"LOCALAPPDATA": r"C:\Users\Lenovo\AppData\Local"},
        python_version=(3, 11),
    )
    assert path == Path(r"C:\Users\Lenovo\AppData\Local/COCOAID/venvs/phase11_py311")
    assert str(project) not in str(path)
    deepest_lxml_member = path / "Lib/site-packages/lxml/isoschematron/resources/xsl/iso-schematron-xslt1/iso_schematron_skeleton_for_xslt1.xsl"
    assert len(str(deepest_lxml_member)) < 260


def test_environment_override_is_supported() -> None:
    path = select_environment_path(
        project=ROOT,
        platform="win32",
        environ={"COCOAID_VENV_DIR": r"D:\envs\cocoaid"},
        python_version=(3, 11),
    )
    assert path == Path(r"D:\envs\cocoaid")


def test_windows_launchers_use_shared_activation_helper() -> None:
    for name in (
        "run.bat",
        "test.bat",
        "check_weather_provider.bat",
        "import_farmer_registry.bat",
        "rebuild_models.bat",
    ):
        text = (ROOT / name).read_text(encoding="utf-8").lower()
        assert "scripts\\activate_environment.bat" in text
        assert ".venv\\scripts\\activate.bat" not in text


def test_setup_preinstalls_binary_lxml_in_external_environment() -> None:
    text = (ROOT / "setup.bat").read_text(encoding="utf-8").lower()
    assert "scripts\\environment_paths.py --ensure" in text
    assert "--only-binary=:all:" in text
    assert '"lxml>=5.3,<7"' in text
    assert "pip_no_cache_dir=1" in text
    assert "import lxml.etree" in text
    assert "scripts\\verify_phase6_2.py" in text
    assert "-m venv .venv" not in text


def test_requirements_explicitly_pin_lxml_range() -> None:
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "lxml>=5.3,<7" in requirements
