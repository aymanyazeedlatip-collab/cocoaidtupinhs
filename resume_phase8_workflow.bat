@echo off
setlocal
cd /d "%~dp0"
call scripts\activate_environment.bat
if errorlevel 1 (
  pause
  exit /b 1
)
echo.
echo This resumes Phase 8 from the pest-assessment step.
echo Keep run.bat open before continuing.
echo You will be asked for the production forecast ID and pest observation ID.
echo.
python scripts\resume_phase8_workflow.py
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if not "%EXIT_CODE%"=="0" (
  echo PHASE 8 RESUME WORKFLOW FAILED.
  echo Copy the complete message above when asking for help.
) else (
  echo PHASE 8 RESUME WORKFLOW COMPLETE.
)
pause
exit /b %EXIT_CODE%
