@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv. Run setup first.
  pause
  exit /b 1
)
echo Capturing two consecutive whole-dialogue streams and their structural context.
echo This is log-only and will not pause or modify PPSSPP.
".venv\Scripts\python.exe" "tools\dialogue_context_probe.py"
set ERR=%ERRORLEVEL%
if not "%ERR%"=="0" echo Probe failed with exit code %ERR%.
pause
exit /b %ERR%
