@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Missing .venv\Scripts\python.exe
    echo Run scripts\setup.ps1 first.
    pause
    exit /b 1
)

echo Differential dialogue probe
 echo.
echo Start with the current dialogue box visible.
echo The script will capture it twice, then ask you to advance EXACTLY ONE box.
echo.

.venv\Scripts\python.exe tools\dialogue_diff_probe.py
set ERR=%ERRORLEVEL%
if not "%ERR%"=="0" echo Probe failed with exit code %ERR%.

echo.
pause
exit /b %ERR%
