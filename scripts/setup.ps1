$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
if (!(Test-Path ".venv/Scripts/python.exe")) {
  py -m venv .venv
  if ($LASTEXITCODE -ne 0) { throw "Falha ao criar ambiente Python." }
}
& ".venv/Scripts/python.exe" -m pip install -r requirements-lock.txt
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar dependências." }
& ".venv/Scripts/python.exe" scripts/configure.py
if ($LASTEXITCODE -ne 0) { throw "Falha ao configurar .env." }
Write-Host "Configuração pronta. Segredos locais estão no .env."
