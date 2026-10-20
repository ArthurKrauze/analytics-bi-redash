$ErrorActionPreference = "Stop"
if (!(Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host "Arquivo .env criado. Edite credenciais do MySQL e segredos do Redash."
} else {
  Write-Host "Arquivo .env já existe; preservado."
}
py -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
Write-Host "Dependências instaladas. Agora configure .env e siga o README."
