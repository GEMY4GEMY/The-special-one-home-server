# Local AI runtime — Windows helper
# Requires Ollama installed separately and a compatible model downloaded once.
param([string]$Model = "qwen3-vl:32b-thinking")
$ErrorActionPreference = "Stop"
$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) {
    Write-Host "Ollama was not found. Install a compatible local runtime first."
    exit 1
}
Write-Host "Checking local model: $Model"
& ollama list
if ($LASTEXITCODE -ne 0) { throw "Unable to contact Ollama" }
Write-Host "To download the configured model once, run: ollama pull $Model"
Write-Host "Do not start a second runtime if Ollama is already running."
Write-Host "AI endpoint: http://127.0.0.1:11434/api/chat"
Write-Host "Model identifier must match an actually installed model."
