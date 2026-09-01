@echo off
setlocal
set "DIR=%~dp0analysis\debugger"
if not exist "%DIR%" (
  echo No analysis\debugger directory exists.
  pause
  exit /b 0
)
echo Deleting local debugger captures from:
echo   %DIR%
echo.
del /q "%DIR%\*.png" 2>nul
del /q "%DIR%\*.jpg" 2>nul
del /q "%DIR%\*.jpeg" 2>nul
del /q "%DIR%\*.webp" 2>nul
echo Done. JSON, BIN, and other analysis files were preserved.
pause
