@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv. Run setup first.
  pause
  exit /b 1
)
echo Reversible complete-JP proof for the visible "Muy bien, Boku" textbox.
echo Stream, atlas, and the isolated 16-pixel JP advance are checked and restored.
".venv\Scripts\python.exe" "tools\known_line_swap_probe.py"
set ERR=%ERRORLEVEL%
if not "%ERR%"=="0" echo Probe failed with exit code %ERR%.
pause
exit /b %ERR%
