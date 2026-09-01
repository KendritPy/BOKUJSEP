@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv. Run setup first.
  pause
  exit /b 1
)
echo Classifying stable-diff candidates against PPSSPP's known function/module map...
".venv\Scripts\python.exe" "tools\classify_diff_candidates.py"
set ERR=%ERRORLEVEL%
if not "%ERR%"=="0" echo Classifier failed with exit code %ERR%.
pause
exit /b %ERR%
