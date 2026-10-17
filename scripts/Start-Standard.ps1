$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $root
$python = Join-Path $root 'runtime\python.exe'
if (-not (Test-Path $python)) { throw 'Embedded Python runtime missing.' }
$env:TSO_ADMIN_USERNAME = 'Mrsameh'
$env:TSO_DB_PATH = Join-Path $root 'backend\data\standard.sqlite3'
if (-not (Test-Path $env:TSO_DB_PATH)) {
    $secret = Read-Host 'Choose administrator password (at least 12 characters)' -AsSecureString
    if ($secret.Length -lt 12) { throw 'Password too short' }
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
    try {
        $env:TSO_ADMIN_INITIAL_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
        & $python -c 'from backend.app import initialize; initialize()'
        if ($LASTEXITCODE -ne 0) { throw 'Database setup failed' }
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
        Remove-Item Env:TSO_ADMIN_INITIAL_PASSWORD -ErrorAction SilentlyContinue
    }
}
Write-Host 'THE SPECIAL ONE Standard - No AI required'
Start-Process 'http://localhost:100/standard-home'
& $python -m uvicorn backend.standard_app:app --host 0.0.0.0 --port 100 --workers 1
