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
$ollama = Join-Path $root 'ai-engine\ollama.exe'
if (Test-Path $ollama) {
    $env:OLLAMA_MODELS = Join-Path $root 'ai-models'
    New-Item -ItemType Directory -Force $env:OLLAMA_MODELS | Out-Null
    $env:OLLAMA_HOST = '127.0.0.1:11434'
    $env:TSO_AI_URL = 'http://127.0.0.1:11434/api/chat'
    $env:TSO_AI_MODEL = 'qwen3-vl:4b'
    $available = @()
    try {
        $models = & $ollama list 2>$null
        $available = @($models)
    } catch {}
    if (-not ($available -match 'qwen3-vl:')) {
        Start-Process -FilePath $ollama -ArgumentList 'serve' -WindowStyle Hidden
        Start-Sleep -Seconds 3
        try { $available = @(& $ollama list 2>$null) } catch {}
    }
    foreach ($candidate in @('qwen3-vl:4b','qwen3-vl:2b')) {
        if ($available -match [regex]::Escape($candidate)) {
            $env:TSO_AI_MODEL = $candidate
            Write-Host ('Local AI model: ' + $candidate)
            break
        }
    }
    if (-not ($available -match 'qwen3-vl:')) {
        Write-Warning 'Ollama engine included, but no local Qwen3-VL model is bundled. AI features require a model pack.'
    }
}
Write-Host 'Starting THE SPECIAL ONE at http://localhost:100'
Start-Process 'http://localhost:100'
& $python -m uvicorn backend.app:app --host 0.0.0.0 --port 100 --workers 1
if ($LASTEXITCODE -ne 0) { throw 'Server stopped with an error.' }
