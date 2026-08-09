@echo off
setlocal
cd /d "%~dp0"
call scripts\activate_environment.bat
if errorlevel 1 (
  pause
  exit /b 1
)
python scripts\check_weather_provider.py
echo.
if errorlevel 1 (
  echo WEATHER PROVIDER CHECK FAILED.
  echo Copy the full diagnostic output when asking for help.
) else (
  echo WEATHER PROVIDER CHECK PASSED.
)
pause
