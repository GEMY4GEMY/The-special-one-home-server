$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $root
$python = Join-Path $root 'runtime\python.exe'
if (-not (Test-Path $python)) { throw 'Embedded Python runtime missing.' }
$env:TSO_ADMIN_USERNAME = 'Mrsameh'
$env:TSO_EDITION = 'standard'
$dataDir = Join-Path $root 'backend\data'
New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
$env:TSO_DB_PATH = Join-Path $dataDir 'standard.sqlite3'
$env:TSO_ADMIN_INITIAL_PASSWORD = ''
try {
    # Do not use DB file existence as a proxy for admin account existence.
    # A database may already exist after an interrupted first launch.
    $needsAdmin = & $python (Join-Path $root 'scripts\Check-Standard-Admin.py')
    if ($LASTEXITCODE -ne 0) { throw 'Unable to inspect administrator account' }
    $adminCheck = [string]($needsAdmin | Select-Object -Last 1)
    if ($adminCheck.Trim() -eq 'YES') {
        Write-Host 'First-time administrator setup. Username: Mrsameh'
        $secret = Read-Host 'Set a NEW administrator password (12 characters minimum)' -AsSecureString
        if ($secret.Length -lt 12) { throw 'Administrator password must contain at least 12 characters' }
        $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
        try {
            $env:TSO_ADMIN_INITIAL_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
            & $python (Join-Path $root 'scripts\Initialize-Standard-Admin.py')
            if ($LASTEXITCODE -ne 0) { throw 'Administrator setup failed' }
        } finally {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
        }
    }
} finally {
    Remove-Item Env:TSO_ADMIN_INITIAL_PASSWORD -ErrorAction SilentlyContinue
}
Write-Host 'THE SPECIAL ONE Standard | Admin username: Mrsameh | Port: 200'
Write-Host 'Open http://localhost:200/standard-home (NOT the older AI portal at /)'
Start-Process 'http://localhost:200/standard-home'
& $python -m uvicorn backend.standard_app:app --host 0.0.0.0 --port 200 --workers 1
