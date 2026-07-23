# Instalación local de JDM Empeños en Windows (PowerShell)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> JDM Empeños · instalación local" -ForegroundColor Cyan

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python no está instalado o no está en el PATH."
}

python -m venv .venv
& .\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Archivo .env creado desde .env.example" -ForegroundColor Yellow
}

New-Item -ItemType Directory -Force -Path "instance", "uploads" | Out-Null

$env:FLASK_APP = "run.py"
flask db init 2>$null
flask db migrate -m "fase1_inicial" 2>$null
flask db upgrade

python scripts\create_superadmin.py

Write-Host ""
Write-Host "Instalación completada." -ForegroundColor Green
Write-Host "Active el entorno: .\.venv\Scripts\Activate.ps1"
Write-Host "Ejecute: python run.py"
Write-Host "Abra: http://127.0.0.1:5000"