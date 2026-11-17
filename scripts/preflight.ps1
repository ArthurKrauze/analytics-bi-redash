$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
foreach ($cmd in @("git", "docker", "py")) {
  if (!(Get-Command $cmd -ErrorAction SilentlyContinue)) { throw "Pré-requisito ausente: $cmd" }
}
docker compose version
if ($LASTEXITCODE -ne 0) { throw "Docker Compose indisponível." }
docker info --format '{{.ServerVersion}}'
if ($LASTEXITCODE -ne 0) { throw "Abra o Docker Desktop e aguarde o engine iniciar." }
Write-Host "Verifique as portas 3307 (MySQL), 27017 (MongoDB) e 5000 (Redash)."
Write-Host "O Compose inclui o MySQL e o projeto gera o TPC-H automaticamente."
