@echo off
rem Shared activation helper. Intentionally no SETLOCAL: activation must persist in the caller.
set "COCOAID_ENV_POINTER=%~dp0..\.cocoaid_venv_path"
set "COCOAID_VENV="
if exist "%COCOAID_ENV_POINTER%" set /p COCOAID_VENV=<"%COCOAID_ENV_POINTER%"
if not defined COCOAID_VENV (
  echo COCOAID environment pointer is missing. Run setup.bat first.
  exit /b 1
)
if not exist "%COCOAID_VENV%\Scripts\activate.bat" (
  echo COCOAID environment was not found at:
  echo   %COCOAID_VENV%
  echo Run setup.bat to recreate it.
  exit /b 1
)
call "%COCOAID_VENV%\Scripts\activate.bat"
if errorlevel 1 exit /b 1
exit /b 0
