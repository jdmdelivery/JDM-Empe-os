# Empaquetado local Windows (.exe) — JDM Empeños
# Uso: .\scripts\build_exe.ps1

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Error "Active o cree el entorno virtual primero (scripts\install_local.ps1)."
}

.\.venv\Scripts\python.exe -m pip install --upgrade pyinstaller
.\.venv\Scripts\pyinstaller.exe --noconfirm --clean `
  --name "JDM_Empenos" `
  --add-data "app/templates;app/templates" `
  --add-data "app/static;app/static" `
  --hidden-import "reportlab" `
  --hidden-import "openpyxl" `
  --hidden-import "qrcode" `
  run.py

Write-Host ""
Write-Host "Listo: dist\JDM_Empenos\JDM_Empenos.exe"
Write-Host "Coloque un .env junto al exe (SECRET_KEY, SQLite) y ejecute migraciones en primer arranque."
