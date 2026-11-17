$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
& "$PSScriptRoot/setup.ps1"
$python = Join-Path (Get-Location) ".venv/Scripts/python.exe"
foreach ($module in @("etl.native", "etl.seed", "etl.migrate", "etl.validate", "etl.evidence")) {
  & $python -m $module
  if ($LASTEXITCODE -ne 0) { throw "Falha em $module. Corrija o erro antes de continuar." }
}
Write-Host "ETL e evidências prontas sem Docker. Redash requer outro ambiente com containers."
