@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv. Run setup first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" "tools\dialogue_stable_diff_probe.py"
set code=%errorlevel%
if not "%code%"=="0" echo Probe failed with exit code %code%.
pause
exit /b %code%
