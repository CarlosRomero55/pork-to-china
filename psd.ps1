# psd.ps1 · Fase 4.3a · Pork to China
# Descarga el balance de carne de cerdo de USDA PSD (todos los países + mundo) a bronze
# y muestra el reporte de descubrimiento con la estructura real de la API.
# Uso (en PowerShell, dentro de D:\pork-to-china):   .\psd.ps1

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
# Python escribe en UTF-8 y PowerShell lo lee en UTF-8 (tildes y símbolos correctos, también con tuberías)
$env:PYTHONUTF8 = "1"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$venvPy = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) { Write-Host "Primero ejecuta .\setup.ps1" -ForegroundColor Red; exit 1 }

& $venvPy -m src.extract_psd
if ($LASTEXITCODE -ne 0) { Write-Host "`nLa extracción de USDA falló; pégale esta salida a Claude (y las últimas líneas de logs\pipeline.log)." -ForegroundColor Red; exit 1 }
Write-Host "`nExtracción USDA completa. Pégale esta salida a Claude." -ForegroundColor Green
