@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv. Run setup first.
  pause
  exit /b 1
)
echo Fast targeted differential over only the pages that survived the corrected full-RAM probe.
echo Reload the known textbox before running this.
".venv\Scripts\python.exe" "tools\dialogue_targeted_diff_probe.py"
set ERR=%ERRORLEVEL%
if not "%ERR%"=="0" echo Probe failed with exit code %ERR%.
pause
exit /b %ERR%
