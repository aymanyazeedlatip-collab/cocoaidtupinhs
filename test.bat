@echo off
setlocal
cd /d "%~dp0"
set "OMP_NUM_THREADS=1"
set "OPENBLAS_NUM_THREADS=1"
set "MKL_NUM_THREADS=1"
set "NUMEXPR_NUM_THREADS=1"
set "VECLIB_MAXIMUM_THREADS=1"
set "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1"
call scripts\activate_environment.bat
if errorlevel 1 (
  pause
  exit /b 1
)
python scripts\run_test_suite.py
pause
