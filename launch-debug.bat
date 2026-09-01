@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\launch-dev.ps1" -Interpreter %*
exit /b %errorlevel%
