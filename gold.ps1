# gold.ps1 · Fase 7 · Pork to China
# Aplica migraciones, reconstruye gold desde silver (dimensiones, importaciones de China y
# arancel aplicado), concilia gold = silver y corre todas las pruebas.
# Uso (en PowerShell, dentro de D:\pork-to-china):   .\gold.ps1

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
# Python escribe en UTF-8 y PowerShell lo lee en UTF-8 (tildes y símbolos correctos)
$env:PYTHONUTF8 = "1"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$venvPy = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) { Write-Host "Primero ejecuta .\setup.ps1" -ForegroundColor Red; exit 1 }

& $venvPy -m src.migrate
if ($LASTEXITCODE -ne 0) { Write-Host "`nLas migraciones fallaron; pégale esta salida a Claude." -ForegroundColor Red; exit 1 }

Write-Host ""
& $venvPy -m src.build_gold
if ($LASTEXITCODE -ne 0) { Write-Host "`nGold no cuadra con silver; pégale esta salida a Claude." -ForegroundColor Red; exit 1 }

Write-Host "`n=== Suite de pruebas (pytest) ===" -ForegroundColor Cyan
& $venvPy -m pytest tests -q -p no:warnings
if ($LASTEXITCODE -ne 0) { Write-Host "`nAlguna prueba falló; pégale esta salida a Claude." -ForegroundColor Red; exit 1 }
Write-Host "`nFase 7 completa: gold listo para el análisis y el tablero." -ForegroundColor Green
