from __future__ import annotations

from pathlib import Path

from app.core.config import Settings

ROOT = Path(__file__).resolve().parents[2]


def test_phase_11_3_23_deployment_files_exist() -> None:
    for relative in (
        '.python-version', 'requirements.deploy.txt', 'render.yaml', 'render.free-demo.yaml',
        'vercel.mjs', 'DEPLOYMENT_ENV.example', 'scripts/start_production.sh',
        'scripts/build_vercel_frontend.mjs',
    ):
        assert (ROOT / relative).is_file(), relative


def test_persistent_data_dir_routes_runtime_writes(tmp_path: Path) -> None:
    settings = Settings(_env_file=None, persistent_data_dir=tmp_path)
    assert settings.database_path == tmp_path / 'coco_aid.sqlite3'
    assert settings.reports_dir == tmp_path / 'reports'
    assert settings.cache_dir == tmp_path / 'cache'
    assert settings.private_settings_path == tmp_path / 'private_settings.json'


def test_explicit_runtime_path_override_wins(tmp_path: Path) -> None:
    custom_db = tmp_path / 'custom.sqlite3'
    settings = Settings(_env_file=None, persistent_data_dir=tmp_path / 'disk', database_path=custom_db)
    assert settings.database_path == custom_db
    assert settings.reports_dir == tmp_path / 'disk' / 'reports'


def test_render_blueprint_uses_persistent_single_instance_backend() -> None:
    text = (ROOT / 'render.yaml').read_text(encoding='utf-8')
    assert 'plan: standard' in text
    assert 'region: singapore' in text
    assert 'mountPath: /var/data/cocoaid' in text
    assert 'PERSISTENT_DATA_DIR' in text
    assert 'AUTO_PHASE_WORKFLOWS' in text
    assert 'numInstances: 1' in text
    assert 'requirements.deploy.txt' in text
    assert 'scripts/start_production.sh' in text


def test_vercel_configuration_uses_backend_environment_variable() -> None:
    text = (ROOT / 'vercel.mjs').read_text(encoding='utf-8')
    assert 'COCOAID_BACKEND_URL' in text
    assert "/api/:path*" in text
    assert 'build_vercel_frontend.mjs' in text
    assert 'vercel_dist' in text


def test_deployment_requirements_exclude_test_only_packages() -> None:
    requirements = (ROOT / 'requirements.deploy.txt').read_text(encoding='utf-8')
    assert 'pytest' not in requirements
    assert 'respx' not in requirements
    assert 'scikit-learn==1.9.0' in requirements
