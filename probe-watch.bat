@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv. Run setup/bootstrap first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" "tools\dialogue_watch_probe.py"
set RC=%ERRORLEVEL%
if not "%RC%"=="0" echo Probe failed with exit code %RC%.
pause
exit /b %RC%
