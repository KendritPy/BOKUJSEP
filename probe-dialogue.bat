@echo off
setlocal
set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo Missing Python environment. Run scripts\bootstrap.ps1 first.
  exit /b 1
)
if not exist "%~dp0data\es\dialogue.json" (
  echo Missing extracted dialogue database. Run scripts\pipeline.ps1 first.
  exit /b 1
)
"%PY%" "%~dp0tools\live_dialogue_probe.py" --json "%~dp0analysis\debugger\live-dialogue.json" %*
set "ERR=%ERRORLEVEL%"
echo.
if not "%ERR%"=="0" echo Probe failed with exit code %ERR%.
pause
exit /b %ERR%
