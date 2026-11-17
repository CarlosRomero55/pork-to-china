# extract_hist.ps1 · Fase 14.2 · Pork to China
# Baja de UN Comtrade los años 2015-2017 (importaciones de China y datos espejo) para la serie de tiempo
# interrumpida. Son 6 consultas a la API con tu llave del .env (nunca se muestra).
# Uso (en PowerShell, dentro de D:\pork-to-china):   .\extract_hist.ps1
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
$env:PYTHONUTF8 = "1"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$venvPy = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) { Write-Host "Primero ejecuta .\setup.ps1" -ForegroundColor Red; exit 1 }

& $venvPy -m src.extract_comtrade --start-year 2015 --end-year 2017 --groups CHN,MIRROR --no-availability
if ($LASTEXITCODE -ne 0) { Write-Host "`nLa extracción falló; pégale esta salida a Claude." -ForegroundColor Red; exit 1 }
Write-Host "`nListo: 2015-2017 en bronze. NO corras pipeline.ps1 todavía; avísale a Claude." -ForegroundColor Green
