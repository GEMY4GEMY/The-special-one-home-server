# Run as Administrator after initial manual bootstrap and installing dependencies.
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = Join-Path $root '.venv\Scripts\python.exe'
if (!(Test-Path $python)) { throw 'Missing .venv. Install Python dependencies first.' }
$serviceName = 'TheSpecialOneHomeServer'
$database = Join-Path $root 'backend\data\local.sqlite3'
if (!(Test-Path $database)) { throw 'Run the server once interactively to create the admin account before installing the service.' }
& $python (Join-Path $root 'backend\windows_service.py') --startup auto install
if ($LASTEXITCODE -ne 0) { throw 'Windows service installation failed' }
& sc.exe failure $serviceName 'reset= 86400' 'actions= restart/5000/restart/10000/restart/30000'
if ($LASTEXITCODE -ne 0) { throw 'Service recovery configuration failed' }
& sc.exe failureflag $serviceName 1
& sc.exe start $serviceName
if ($LASTEXITCODE -ne 0) { throw 'Service failed to start; check Windows Event Viewer' }
Write-Host 'Service installed. Health check: http://localhost:100/health'
