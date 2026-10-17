# First-run launcher. Double-click START_THE_SPECIAL_ONE.bat; no manual shell commands.
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $root
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host 'Windows will request administrator permission to install the server service.'
    Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + $PSCommandPath + '"')
    ) -Wait
    exit
}
$serviceName = 'TheSpecialOneHomeServer'
$service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if ($service) {
    if ($service.Status -ne 'Running') { Start-Service -Name $serviceName }
    Start-Process 'http://localhost:100/'
    Write-Host 'THE SPECIAL ONE server is starting on port 100.'
    exit
}
$pythonLauncher = Get-Command py -ErrorAction SilentlyContinue
if (-not $pythonLauncher) {
    throw 'Python is not installed. A standalone EXE installer is planned; this source launcher requires Python 3.11+.'
}
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    & py -3 -m venv (Join-Path $root '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Unable to create Python environment.' }
}
& $python -m pip install -r (Join-Path $root 'backend\requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Unable to install server dependencies.' }
& $python -m pip install pywin32
if ($LASTEXITCODE -ne 0) { throw 'Unable to install Windows service dependency.' }
$dbFile = Join-Path $root 'backend\data\local.sqlite3'
if (-not (Test-Path $dbFile)) {
    $secret = Read-Host 'Choose a NEW administrator password (input hidden)' -AsSecureString
    if ($secret.Length -lt 12) { throw 'Admin password must have at least 12 characters.' }
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
    try {
        $env:TSO_ADMIN_USERNAME = 'Mrsameh'
        $env:TSO_ADMIN_INITIAL_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
        & $python -c 'from backend.app import initialize; initialize()'
        if ($LASTEXITCODE -ne 0) { throw 'Database initialization failed.' }
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
        Remove-Item Env:TSO_ADMIN_INITIAL_PASSWORD -ErrorAction SilentlyContinue
    }
}
& $python (Join-Path $root 'backend\windows_service.py') --startup auto install
if ($LASTEXITCODE -ne 0) { throw 'Service registration failed.' }
& sc.exe failure $serviceName 'reset= 86400' 'actions= restart/5000/restart/10000/restart/30000'
if ($LASTEXITCODE -ne 0) { throw 'Service recovery configuration failed.' }
& sc.exe failureflag $serviceName 1
& sc.exe start $serviceName
if ($LASTEXITCODE -ne 0) { throw 'Service failed to start. Check Event Viewer.' }
Write-Host 'THE SPECIAL ONE is installed and will auto-start with Windows.'
Start-Process 'http://localhost:100/'
