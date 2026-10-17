@echo off
setlocal
cd /d "%~dp0.."
if not defined TSO_ADMIN_INITIAL_PASSWORD (
  echo TSO_ADMIN_INITIAL_PASSWORD must be configured securely on this PC.
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo Missing Python virtual environment. See README.
  exit /b 1
)
".venv\Scripts\python.exe" -m uvicorn backend.app:app --host 0.0.0.0 --port 100
