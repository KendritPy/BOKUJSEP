@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv. Run setup first.
  pause
  exit /b 1
)
echo Targeting candidate word 0x0881C62C from probe-stable-diff.
echo IMPORTANT: use launch-debug.bat / interpreter mode before this probe.
echo This version waits for PPSSPP's real cpu.breakpoint.hit event; F8 is no longer used.
".venv\Scripts\python.exe" "tools\dialogue_watch_event_probe.py" --address 0x0881C62C --size 4 --output "analysis\debugger\dialogue-watch-line.json"
set ERR=%ERRORLEVEL%
if not "%ERR%"=="0" echo Probe failed with exit code %ERR%.
pause
exit /b %ERR%
