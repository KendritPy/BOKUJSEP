@echo off
setlocal
cd /d "%~dp0"
echo Starting PPSSPP without a game so LunaTranslator can attach first.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\launch-dev.ps1" -NoGame %*
if errorlevel 1 pause
exit /b %errorlevel%
