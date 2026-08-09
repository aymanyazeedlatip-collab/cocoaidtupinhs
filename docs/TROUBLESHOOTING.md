# Troubleshooting

## Python is not found

Install Python 3.11 from python.org and enable **Add Python to PATH**, then rerun `setup.bat`.

## Dependency installation fails

- Confirm internet access.
- Phase 6.2 stores the virtual environment under `%LOCALAPPDATA%\COCOAID\venvs` to avoid Windows `MAX_PATH` failures. Do not copy an older `.venv` into the project.
- Extract the flat release ZIP into a new folder, preferably `C:\COCOAID\P6_2`, then rerun `setup.bat`.
- If setup reports an incomplete external environment, delete only the specific environment path printed by setup and rerun it.
- Avoid OneDrive-controlled or administrator-protected folders when possible.

## lxml installation reports a missing deep XSL file

This is the Windows long-path failure corrected in Phase 6.2. Use the Phase 6.2 release, extract it into a new folder, and run its `setup.bat`. The installer creates a short environment outside the project and installs the prebuilt `lxml` wheel before the remaining requirements. Windows registry changes are not required for the corrected installer.

## The browser does not open

Open `http://127.0.0.1:8000` manually after `run.bat` starts.

## Map or charts are blank

The default lightweight interface loads Leaflet, Leaflet Draw, and Chart.js from public CDNs. Check internet access, browser extensions, DNS filtering, and the browser console. Core backend analysis remains available through `/docs`.

## Live weather says provider limited or unavailable

The provider may have returned HTTP 429 or failed. Wait at least five minutes, avoid repeated map requests, or use cached data. Long-term analysis does not require live weather.

## Simulation is slow

Use 100 or 500 runs while testing. Use 1,000 runs for the normal demonstration. A 5,000-run simulation is intentionally heavier.

## Tree-state validation error

Make sure Young + Productive + Aging + Stressed + Infested + Recovering + Dead equals Total Trees.

## Report does not generate

Run **Full Analysis** first. Confirm that the `reports_generated` folder is writable.

## Complete diagnostic

Run `test.bat`. Copy the full terminal output when reporting a problem.

## Simulation appears frozen or CPU usage is unusually high

Version 1.1 limits OpenBLAS, MKL, OpenMP, NumExpr, and Accelerate to one numerical thread before NumPy and scikit-learn load. Use the supplied `run.bat` rather than launching from an old terminal that has already imported numerical libraries. Close old COCO-AID Python processes before starting the new version.

## Farm Site Forecast has no real short-term dates

The long-term module still works. Check the Live Weather source status. Provider unavailability, offline mode, or rate limiting causes the endpoint to skip the provider merge and label every date as a stochastic climate simulation. It never fabricates live data.

## Weather viewer does not show my farm

Return to Farm Setup, draw the polygon or confirm the coordinates, then press **Sync Farm Site** in Live Weather. The parent page also syncs automatically when the embedded viewer loads and after a polygon is drawn or edited.
