$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
function Invoke-Checked {
  param([string]$Program, [string[]]$Arguments)
  & $Program @Arguments
  if ($LASTEXITCODE -ne 0) { throw "Falha em $Program. Corrija o erro acima antes de continuar." }
}
& "$PSScriptRoot/setup.ps1"
$python = Join-Path (Get-Location) ".venv/Scripts/python.exe"
Invoke-Checked $python @("scripts/validate-files.py")
Invoke-Checked "docker" @("compose", "config", "--quiet")
Invoke-Checked "docker" @("compose", "up", "-d", "--wait", "mysql", "mongodb", "postgres", "redis")
Invoke-Checked $python @("-m", "etl.seed")
Invoke-Checked $python @("-m", "etl.migrate")
Invoke-Checked $python @("-m", "etl.validate")
Invoke-Checked $python @("-m", "etl.evidence")
$exists = & docker compose exec -T postgres psql -U redash -d redash -tAc "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='users')"
if ($LASTEXITCODE -ne 0) { throw "Falha ao verificar metadados Redash." }
if (($exists | Out-String).Trim() -ne "t") {
  Invoke-Checked "docker" @("compose", "run", "--rm", "server", "create_db")
}
Invoke-Checked "docker" @("compose", "up", "-d", "server", "worker", "scheduler")
Invoke-Checked $python @("-m", "etl.redash_setup")
Write-Host "Projeto executado. Consulte artifacts/ANALISE_GERENCIAL.md e artifacts/redash.json."
