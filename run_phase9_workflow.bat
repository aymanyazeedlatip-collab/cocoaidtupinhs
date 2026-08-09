@echo off
setlocal
cd /d "%~dp0"
call scripts\activate_environment.bat
if errorlevel 1 (
  pause
  exit /b 1
)
echo.
echo COCOAID PHASE 9 INTEGRATED DECISION-SUPPORT WORKFLOW
echo Keep run.bat open before continuing.
echo You will be asked for the production forecast ID and pest observation ID.
echo The script generates valid JSON automatically and completes Phases 6-9 integration.
echo.
python scripts\run_phase9_workflow.py
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if not "%EXIT_CODE%"=="0" (
  echo PHASE 9 WORKFLOW FAILED.
  echo Copy the complete message above when asking for help.
) else (
  echo PHASE 9 WORKFLOW COMPLETE.
)
pause
exit /b %EXIT_CODE%
