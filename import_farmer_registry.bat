@echo off
setlocal
cd /d "%~dp0"
call scripts\activate_environment.bat
if errorlevel 1 (
  pause
  exit /b 1
)
echo =====================================================
echo COCOAID Restricted Farmer Registry Import
echo =====================================================
echo This imports personally identifiable farmer records into the local SQLite database.
echo Names remain in protected tables and are not returned by public API endpoints.
echo.
python scripts\import_farmer_registry.py --dry-run
if errorlevel 1 goto :fail
echo.
choice /M "Proceed with the full local import"
if errorlevel 2 exit /b 0
python scripts\database_backup.py backup
if errorlevel 1 goto :fail
python scripts\import_farmer_registry.py
if errorlevel 1 goto :fail
echo.
echo IMPORT COMPLETE.
pause
exit /b 0
:fail
echo.
echo IMPORT FAILED. No completed import should be trusted until the error is resolved.
pause
exit /b 1
