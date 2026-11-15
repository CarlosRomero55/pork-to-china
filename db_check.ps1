# db_check.ps1 · Fase 3 · Pork to China
# Autoprueba de la conexión Python <-> MySQL y suite de pruebas. No deja datos en la base.
# Uso (en PowerShell, dentro de D:\pork-to-china):   .\db_check.ps1

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
# Python escribe en UTF-8 y PowerShell lo lee en UTF-8 (tildes y símbolos correctos, también con tuberías)
$env:PYTHONUTF8 = "1"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$venvPy = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) { Write-Host "Primero ejecuta .\setup.ps1" -ForegroundColor Red; exit 1 }

& $venvPy -m src.db
if ($LASTEXITCODE -ne 0) { Write-Host "`nLa autoprueba falló; pégale esta salida a Claude." -ForegroundColor Red; exit 1 }

Write-Host "`n=== Suite de pruebas (pytest) ===" -ForegroundColor Cyan
& $venvPy -m pytest tests -q
if ($LASTEXITCODE -ne 0) { Write-Host "`nAlguna prueba falló; pégale esta salida a Claude." -ForegroundColor Red; exit 1 }
Write-Host "`nFase 3 completa." -ForegroundColor Green
