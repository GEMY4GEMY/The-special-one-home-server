@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup-and-start.ps1"
if errorlevel 1 (
 echo.
 echo Setup did not complete. See the message above.
 pause
)
