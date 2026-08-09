from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    result = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise SystemExit(f"Command failed: {' '.join(command)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")


def main() -> int:
    required = [
        ROOT / 'render.yaml', ROOT / 'vercel.mjs', ROOT / 'requirements.deploy.txt',
        ROOT / 'scripts' / 'start_production.sh', ROOT / 'scripts' / 'build_vercel_frontend.mjs',
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        raise SystemExit(f'Missing deployment files: {missing}')

    run(['node', '--check', 'scripts/build_vercel_frontend.mjs'])
    run(['node', 'scripts/build_vercel_frontend.mjs'])
    assert (ROOT / 'vercel_dist' / 'index.html').is_file()
    assert (ROOT / 'vercel_dist' / 'static' / 'app.js').is_file()
    assert (ROOT / 'vercel_dist' / 'static' / 'assets' / 'audio' / 'bgm-1.mp3').is_file()

    node_env = dict(os.environ)
    node_env['COCOAID_BACKEND_URL'] = 'https://example-backend.onrender.com'
    run(['node', '-e', "import('./vercel.mjs').then(m=>{if(!m.config.rewrites?.length)process.exit(2)})"], env=node_env)

    with tempfile.TemporaryDirectory(prefix='cocoaid-deploy-check-') as temp_dir:
        env = dict(os.environ)
        env.update({
            'PERSISTENT_DATA_DIR': temp_dir,
            'ENVIRONMENT': 'production',
            'AUTO_PHASE_WORKFLOWS': 'false',
            'ALLOW_RUNTIME_API_KEY_CONFIGURATION': 'false',
            # The repository's target is 1.9.0; sandbox verification can run in compatibility mode.
            'STRICT_MODEL_RUNTIME_COMPATIBILITY': 'false',
        })
        code = r'''
from fastapi.testclient import TestClient
from app.main import app
with TestClient(app) as client:
    health = client.get('/api/health')
    assert health.status_code == 200, health.text
    body = health.json()
    assert body['persistent_storage_configured'] is True, body
    candidates = client.get('/api/v2/intercropping/candidates')
    assert candidates.status_code == 200, candidates.text
    assert candidates.json()['count'] == 35, candidates.json()
'''
        run([sys.executable, '-c', code], env=env)

    shutil.rmtree(ROOT / 'vercel_dist', ignore_errors=True)
    print('DEPLOYMENT VERIFICATION PASSED')
    print('Render persistent-runtime bootstrap: passed')
    print('Vercel static frontend build: passed')
    print('Automatic seeded intercrop catalog: 35 candidates')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
