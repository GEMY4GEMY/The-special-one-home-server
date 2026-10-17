# Run on the build machine while online, before moving the portable folder offline.
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$ollama = Join-Path $root 'ai-engine\ollama.exe'
if (-not (Test-Path $ollama)) { throw 'Ollama executable not found in ai-engine.' }
$env:OLLAMA_HOST = '127.0.0.1:11434'
$env:OLLAMA_MODELS = Join-Path $root 'ai-models'
New-Item -ItemType Directory -Force $env:OLLAMA_MODELS | Out-Null
$existing = Get-NetTCPConnection -LocalPort 11434 -State Listen -ErrorAction SilentlyContinue
if (-not $existing) {
    $server = Start-Process -FilePath $ollama -ArgumentList 'serve' -PassThru -WindowStyle Hidden
    Start-Sleep -Seconds 5
}
foreach ($model in @('qwen3-vl:4b')) {
    Write-Host ('Downloading model: ' + $model)
    & $ollama pull $model
    if ($LASTEXITCODE -ne 0) { throw ('Failed to download model ' + $model + '. Verify the exact model tag and internet access.') }
}
$installed = & $ollama list
foreach ($required in @('qwen3-vl:4b')) {
    if (-not ($installed -match [regex]::Escape($required))) { throw ('Required model missing: ' + $required) }
}
Write-Host 'Verified compact model in ai-models. Copy the entire portable folder for offline use.'
