$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $root
$python = Join-Path $root 'runtime\python.exe'
if (-not (Test-Path $python)) { throw 'Portable runtime missing. Download the Windows artifact, not source ZIP.' }
$db = Join-Path $root 'backend\data\local.sqlite3'
if (-not (Test-Path $db)) {
    $secret = Read-Host 'Create administrator password (minimum 12 characters)' -AsSecureString
    if ($secret.Length -lt 12) { throw 'Password must be at least 12 characters.' }
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
    try {
        $env:TSO_ADMIN_INITIAL_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
        $env:TSO_ADMIN_USERNAME = 'Mrsameh'
        & $python -c 'from backend.app import initialize; initialize()'
        if ($LASTEXITCODE -ne 0) { throw 'Database initialization failed.' }
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
        Remove-Item Env:TSO_ADMIN_INITIAL_PASSWORD -ErrorAction SilentlyContinue
    }
}
Write-Host 'Starting THE SPECIAL ONE at http://localhost:100'
Start-Process 'http://localhost:100'
& $python -m uvicorn backend.app:app --host 0.0.0.0 --port 100 --workers 1
if ($LASTEXITCODE -ne 0) { throw 'Server stopped with an error.' }
