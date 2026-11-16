# pipeline.ps1 · Fase 8 · Pork to China
# Un solo comando para todo el proceso: migraciones → [extracción] → silver → validación → gold → pruebas.
# Se detiene en la primera etapa que falla y registra cada corrida en pork_bronze.etl_run.
#
# Uso (en PowerShell, dentro de D:\pork-to-china):
#   .\pipeline.ps1                    # sin extracción (usa lo que ya está en bronze)
#   .\pipeline.ps1 -Extract           # descarga datos nuevos de Comtrade y USDA (usa tu llave)
#   .\pipeline.ps1 -From validate     # retoma desde una etapa
param(
  [switch]$Extract,
  [string]$From = ""
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
# Python escribe en UTF-8 y PowerShell lo lee en UTF-8 (tildes y símbolos correctos)
$env:PYTHONUTF8 = "1"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$venvPy = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) { Write-Host "Primero ejecuta .\setup.ps1" -ForegroundColor Red; exit 1 }

$pyArgs = @("-m", "src.pipeline")
if ($Extract) { $pyArgs += "--extract" }
if ($From)    { $pyArgs += @("--from", $From) }

& $venvPy @pyArgs | Where-Object { $_ -notmatch "^INFO" }
$code = $LASTEXITCODE
if ($code -eq 0) { Write-Host "`nPipeline completo: datos actualizados y verificados." -ForegroundColor Green }
elseif ($code -eq 2) { Write-Host "`nYa hay otra corrida en curso; espera a que termine." -ForegroundColor Yellow }
else { Write-Host "`nEl pipeline se detuvo; pégale esta salida a Claude." -ForegroundColor Red }
exit $code
