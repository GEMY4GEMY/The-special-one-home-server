$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$ollama = Join-Path $root 'ai-engine\ollama.exe'
$models = Join-Path $root 'ai-models'
if (-not (Test-Path $ollama)) { throw 'Ollama engine is missing from the Windows bundle.' }
if (-not (Test-Path $models)) { throw 'Offline AI model pack is missing.' }
$env:OLLAMA_HOST = '127.0.0.1:11434'
$env:OLLAMA_MODELS = $models
try {
    $response = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 10
} catch {
    throw 'Ollama is not running. Start the portable server first.'
}
$names = @($response.models | ForEach-Object { $_.name })
foreach ($model in @('qwen3-vl:4b')) {
    if ($names -notcontains $model) { throw ('Missing offline model: ' + $model) }
    Write-Host ('OK: ' + $model)
}
Write-Host 'Offline model availability checks passed.'
