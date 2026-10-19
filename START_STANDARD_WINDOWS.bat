@echo off
setlocal
cd /d "%~dp0"
title THE SPECIAL ONE - Standard Server
echo ===============================================
echo   THE SPECIAL ONE - STANDARD SERVER
echo ===============================================
echo Starting local server. Keep this window open.
echo.
if not exist "%~dp0runtime\python.exe" (
  echo ERROR: Bundled Python is missing.
  echo Extract the FULL release ZIP before running this file.
  pause
  exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Start-Standard.ps1"
set "EXITCODE=%ERRORLEVEL%"
echo.
echo Server stopped. Exit code: %EXITCODE%
echo If there was an error, take a screenshot of this window.
pause
exit /b %EXITCODE%
