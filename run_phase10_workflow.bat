@echo off
setlocal
cd /d "%~dp0"
call scripts\activate_environment.bat
if errorlevel 1 (
  pause
  exit /b 1
)
echo.
echo COCOAID PHASE 10 COCO-PILOT AND FORMAL REPORT WORKFLOW
echo Keep run.bat open before continuing.
echo You will be asked only for the Phase 9 decision-support run ID.
echo The script generates a grounded narrative and verified DOCX and PDF reports.
echo.
python scripts\run_phase10_workflow.py
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if not "%EXIT_CODE%"=="0" (
  echo PHASE 10 WORKFLOW FAILED.
  echo Copy the complete message above when asking for help.
) else (
  echo PHASE 10 WORKFLOW COMPLETE.
)
pause
exit /b %EXIT_CODE%
