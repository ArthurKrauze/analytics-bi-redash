$ErrorActionPreference = "Stop"
Write-Host "=== Pré-requisitos ==="
foreach ($cmd in @("git", "docker", "py")) {
  $found = Get-Command $cmd -ErrorAction SilentlyContinue
  if ($found) { Write-Host "[OK] $cmd" } else { Write-Warning "[FALTA] $cmd" }
}
docker compose version
docker ps --format "table {{.Names}}\t{{.Ports}}"
Write-Host "`nVerifique se as portas 27017 e 5000 estão livres e se o MySQL está acessível."
Write-Host "O MySQL TPC-H NÃO é criado por este projeto."
