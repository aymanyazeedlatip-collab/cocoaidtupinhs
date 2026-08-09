@echo off
setlocal
cd /d "%~dp0"
set "OMP_NUM_THREADS=1"
set "OPENBLAS_NUM_THREADS=1"
set "MKL_NUM_THREADS=1"
set "NUMEXPR_NUM_THREADS=1"
set "VECLIB_MAXIMUM_THREADS=1"
call scripts\activate_environment.bat
if errorlevel 1 (
  pause
  exit /b 1
)
python scripts\prepare_climate_demo.py
if errorlevel 1 goto :fail
python scripts\generate_data.py
if errorlevel 1 goto :fail
python scripts\train_models.py
if errorlevel 1 goto :fail
python scripts\verify_installation.py
if errorlevel 1 goto :fail
echo.
echo MODEL REBUILD COMPLETE.
pause
exit /b 0
:fail
echo.
echo MODEL REBUILD FAILED.
pause
exit /b 1
