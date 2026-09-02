@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv. Run setup first.
  pause
  exit /b 1
)
echo Watching all seven signature-checked Spanish injected-code entry edges.
echo This is log-only and will not pause PPSSPP.
".venv\Scripts\python.exe" "tools\injected_edge_probe.py"
set ERR=%ERRORLEVEL%
if not "%ERR%"=="0" echo Probe failed with exit code %ERR%.
pause
exit /b %ERR%
