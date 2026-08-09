@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "OMP_NUM_THREADS=1"
set "OPENBLAS_NUM_THREADS=1"
set "MKL_NUM_THREADS=1"
set "NUMEXPR_NUM_THREADS=1"
set "VECLIB_MAXIMUM_THREADS=1"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
set "PIP_NO_CACHE_DIR=1"
set "PIP_DEFAULT_TIMEOUT=8"
set "PIP_RETRIES=1"

echo =====================================================
echo COCOAID Setup - Phase 11.3.23 Deployment-Ready Final Build
echo =====================================================
set "PYTHON_CMD="
where py >nul 2>&1
if not errorlevel 1 (
  py -3.11 -c "import sys" >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=py -3.11"
)
if not defined PYTHON_CMD (
  where python >nul 2>&1
  if errorlevel 1 (
    echo ERROR: Python 3.11 or a compatible Python version was not found.
    echo Install Python from https://www.python.org/downloads/ and enable Add Python to PATH.
    pause
    exit /b 1
  )
  set "PYTHON_CMD=python"
)

echo Resolving a short virtual-environment path...
for /f "usebackq delims=" %%V in (`%PYTHON_CMD% scripts\environment_paths.py --path-only`) do set "COCOAID_VENV=%%V"
if not defined COCOAID_VENV (
  echo ERROR: Could not resolve the COCOAID environment path.
  goto :fail
)
echo Project folder: %CD%
echo Python environment: %COCOAID_VENV%
echo The environment is stored outside the project to prevent Windows MAX_PATH errors.

%PYTHON_CMD% scripts\environment_paths.py --ensure --path-only >nul
if errorlevel 1 goto :fail

call scripts\activate_environment.bat
if errorlevel 1 goto :fail

rem Ensure pip exists using Python's bundled ensurepip. This is offline and does not contact PyPI.
python -m pip --version >nul 2>&1
if errorlevel 1 (
  echo Repairing pip from Python's bundled installer...
  python -m ensurepip --upgrade
  if errorlevel 1 goto :fail
)

echo Checking the existing Python environment locally...
python scripts\check_requirements_local.py --quiet
if not errorlevel 1 (
  echo All required Python packages are already installed and compatible.
  echo Skipping PyPI access and dependency installation.
  goto :dependencies_ready
)

echo One or more Python packages are missing or incompatible.
echo Installing only what is needed. Network fallback uses short retries to avoid long stalls.

rem Install lxml from its Windows wheel only when the local environment does not
rem already satisfy the required range. This avoids unnecessary PyPI requests.
python scripts\check_requirements_local.py --quiet --require "lxml>=5.3,<7"
if errorlevel 1 (
  python -m pip install --disable-pip-version-check --retries 1 --timeout 8 --only-binary=:all: "lxml>=5.3,<7"
  if errorlevel 1 (
    echo ERROR: A compatible prebuilt lxml wheel could not be installed.
    echo Check your internet connection, or use 64-bit Python 3.11, then rerun setup.bat.
    goto :fail
  )
)

rem IMPORTANT: no --upgrade flag here. Without --upgrade, pip leaves already
rem satisfied packages alone instead of querying PyPI for newer copies of every package.
python -m pip install --disable-pip-version-check --retries 1 --timeout 8 --prefer-binary -r requirements.txt
if errorlevel 1 goto :fail

python scripts\check_requirements_local.py --quiet
if errorlevel 1 (
  echo ERROR: Python requirements are still incomplete after installation.
  python scripts\check_requirements_local.py
  goto :fail
)

:dependencies_ready
python -m pip check
if errorlevel 1 goto :fail

python -c "import lxml.etree; print('lxml runtime:', lxml.etree.LXML_VERSION)"
if errorlevel 1 goto :fail
python -c "import httpx2; print('HTTPX2 runtime:', httpx2.__version__)"
if errorlevel 1 goto :fail
python -c "import importlib.metadata, truststore; print('System TLS trust-store runtime:', importlib.metadata.version('truststore'))"
if errorlevel 1 goto :fail

if not exist data\climate_demo\philippines_climate_demo.csv python scripts\prepare_climate_demo.py
if errorlevel 1 goto :fail
if not exist data\synthetic\coconut_farm_years.csv python scripts\generate_data.py
if errorlevel 1 goto :fail
python scripts\ensure_models.py
if errorlevel 1 goto :fail
python scripts\initialize_phase2.py
if errorlevel 1 goto :fail
python scripts\verify_installation.py
if errorlevel 1 goto :fail
python scripts\verify_phase3.py
if errorlevel 1 goto :fail
python scripts\verify_phase4.py
if errorlevel 1 goto :fail
python scripts\verify_phase5.py
if errorlevel 1 goto :fail
python scripts\verify_phase6.py
if errorlevel 1 goto :fail
python scripts\verify_phase6_2.py
if errorlevel 1 goto :fail
python scripts\verify_phase7.py
if errorlevel 1 goto :fail
python scripts\verify_phase8.py
if errorlevel 1 goto :fail
python scripts\verify_phase8_1.py
if errorlevel 1 goto :fail
python scripts\verify_phase9.py
if errorlevel 1 goto :fail
python scripts\verify_phase10.py
if errorlevel 1 goto :fail
python scripts\verify_phase11.py
if errorlevel 1 goto :fail

echo.
echo SETUP COMPLETE.
echo Path-safe environment: %COCOAID_VENV%
echo Launching COCO-AID automatically in a new window...
start "COCOAID" cmd /c run.bat
echo COCO-AID is starting and should open in your browser automatically.
timeout /t 2 >nul
exit /b 0

:fail
echo.
echo SETUP FAILED.
echo The project files were not modified destructively.
echo Copy the complete error shown above if assistance is needed.
pause
exit /b 1
