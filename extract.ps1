# extract.ps1 · Fase 4 · Pork to China
# Extrae el comercio de cerdo de UN Comtrade a la capa bronze (incremental, con caché).
# Uso (en PowerShell, dentro de D:\pork-to-china):
#   .\extract.ps1            extracción normal
#   .\extract.ps1 -Refresh   vuelve a pedir todos los años (ignora la caché)
param([switch]$Refresh)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
$venvPy = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) { Write-Host "Primero ejecuta .\setup.ps1" -ForegroundColor Red; exit 1 }

$args_ = @("-m", "src.extract_comtrade")
if ($Refresh) { $args_ += "--refresh" }
& $venvPy @args_
if ($LASTEXITCODE -ne 0) { Write-Host "`nLa extracción falló; pégale esta salida a Claude (y las últimas líneas de logs\pipeline.log)." -ForegroundColor Red; exit 1 }
Write-Host "`nExtracción completa. Pégale esta salida a Claude." -ForegroundColor Green
