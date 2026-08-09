# COCOAID Phase 11.3.6 Test Report

## Automated test inventory
- Unit tests: 252 passed
- Integration tests: 54 passed
- Mathematical tests: 9 passed
- Total: 315 passed

## Release verification
- `scripts/verify_phase11.py`: PASS
- `scripts/verify_installation.py`: PASS
- JavaScript syntax (`app.js`, `phase11.js`): PASS
- Python compilation (`app`, `scripts`): PASS
- CSS parser audit (`phase11.css`): PASS, no parser errors
- Duplicate DOM-ID audit: PASS
- Primary navigation order audit: PASS, Weather GIS is last
- Productivity duplicate Weather GIS iframe audit: PASS, iframe removed
- Phase 11 asset manifests regenerated for interface version 1.3.6

## Fresh runtime smoke check
Fresh Uvicorn process returned HTTP 200 for:
- `/`
- `/api/health`
- `/api/v2/interface/status`
- `/static/phase11.css`
- `/static/app.js`
- `/weather-viewer`

## Environment note
The test container has scikit-learn 1.8.0 while the project pins scikit-learn 1.9.0 for exact serialized-model reproducibility. The application therefore reports legacy compatibility mode in this sandbox. This is not a frontend regression; `requirements.txt` retains the intended runtime pin.
