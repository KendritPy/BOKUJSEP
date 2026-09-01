@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv. Run setup first.
  pause
  exit /b 1
)
echo Watching exact clean halfword 0x0892EBA4 found by the corrected targeted diff.
echo Fresh A->B capture changed it from 0x0063 to 0x01C0.
echo IMPORTANT: use launch-debug.bat / interpreter mode before this probe.
echo The probe now verifies PPSSPP installed WRITE+CHANGE before asking you to advance.
echo PPSSPP 1.20.4 reports the hit as cpu.stepping reason=memory.breakpoint.
".venv\Scripts\python.exe" "tools\dialogue_watch_event_probe.py" --address 0x0892EBA4 --size 2 --output "analysis\debugger\dialogue-watch-glyph.json"
set ERR=%ERRORLEVEL%
if not "%ERR%"=="0" echo Probe failed with exit code %ERR%.
pause
exit /b %ERR%
