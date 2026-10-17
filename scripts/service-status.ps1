$service = Get-Service -Name 'TheSpecialOneHomeServer' -ErrorAction SilentlyContinue
if (!$service) { Write-Host 'Service not installed'; exit 1 }
$service | Format-Table Name, Status, StartType
try {
  $health = Invoke-RestMethod -Uri 'http://localhost:100/health' -TimeoutSec 5
  $health | ConvertTo-Json
} catch {
  Write-Warning 'Service HTTP health check failed'
  exit 2
}
