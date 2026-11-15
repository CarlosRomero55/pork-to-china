# db_setup.ps1 · Fase 2 · Pork to China
# Crea las bases pork_bronze / pork_silver / pork_gold, los usuarios pork_etl y pork_bi,
# siembra los datos de referencia, actualiza .env y corre las pruebas.
# Uso (en PowerShell, dentro de D:\pork-to-china):   .\db_setup.ps1
# Te pedirá: la contraseña de root de MySQL y 2 contraseñas nuevas (se escriben ocultas).

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
# Python escribe en UTF-8 y PowerShell lo lee en UTF-8 (tildes y símbolos correctos, también con tuberías)
$env:PYTHONUTF8 = "1"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$venvPy = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) { Write-Host "Primero ejecuta .\setup.ps1" -ForegroundColor Red; exit 1 }

& $venvPy -m src.db_setup
if ($LASTEXITCODE -ne 0) { Write-Host "`nLa creación de la base falló; pégale esta salida a Claude." -ForegroundColor Red; exit 1 }

Write-Host "`n=== Pruebas de restricciones (pytest) ===" -ForegroundColor Cyan
& $venvPy -m pytest tests/test_schema.py -v
if ($LASTEXITCODE -ne 0) { Write-Host "`nAlguna prueba falló; pégale esta salida a Claude." -ForegroundColor Red; exit 1 }
Write-Host "`nFase 2 completa." -ForegroundColor Green
