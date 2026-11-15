# transform.ps1 · Fase 5 · Pork to China
# Aplica migraciones pendientes y transforma Comtrade de bronze a silver, con reporte de calidad.
# Uso (en PowerShell, dentro de D:\pork-to-china):   .\transform.ps1

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
# Python escribe en UTF-8 y PowerShell lo lee en UTF-8 (tildes y símbolos correctos, también con tuberías)
$env:PYTHONUTF8 = "1"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$venvPy = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) { Write-Host "Primero ejecuta .\setup.ps1" -ForegroundColor Red; exit 1 }

& $venvPy -m src.migrate
if ($LASTEXITCODE -ne 0) { Write-Host "`nLas migraciones fallaron; pégale esta salida a Claude." -ForegroundColor Red; exit 1 }

& $venvPy -m src.harmonize
if ($LASTEXITCODE -ne 0) { Write-Host "`nLa transformación falló; pégale esta salida a Claude." -ForegroundColor Red; exit 1 }

Write-Host "`n=== Suite de pruebas (pytest) ===" -ForegroundColor Cyan
& $venvPy -m pytest tests -q
if ($LASTEXITCODE -ne 0) { Write-Host "`nAlguna prueba falló; pégale esta salida a Claude." -ForegroundColor Red; exit 1 }
Write-Host "`nFase 5 (Comtrade) completa. Pégale esta salida a Claude." -ForegroundColor Green
