@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv. Run setup first.
  pause
  exit /b 1
)
echo Watching first DATA/UNKNOWN survivor from classify-diff: 0x0892EBA4-0x0892EBB1.
echo Its 16-bit values resemble packed 2D glyph/layout coordinates, so this is a renderer-path probe.
echo IMPORTANT: use launch-debug.bat / interpreter mode before this probe.
".venv\Scripts\python.exe" "tools\dialogue_watch_event_probe.py" --address 0x0892EBA4 --size 14 --output "analysis\debugger\dialogue-watch-glyph.json"
set ERR=%ERRORLEVEL%
if not "%ERR%"=="0" echo Probe failed with exit code %ERR%.
pause
exit /b %ERR%
