# snapshot.ps1 · Paso 16.3 · Pork to China
# Exporta la copia pública de gold (data/snapshot/*.parquet) para el tablero en línea (Streamlit Community Cloud).
# Uso (en PowerShell, dentro de la carpeta del proyecto, DESPUÉS de .\pipeline.ps1):   .\snapshot.ps1

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
$env:PYTHONUTF8 = "1"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$venvPy = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) { Write-Host "Primero ejecuta .\setup.ps1" -ForegroundColor Red; exit 1 }

Write-Host "=== Pork to China · copia pública para el tablero en línea ===" -ForegroundColor Cyan
& $venvPy -m pip install -q -r requirements.txt
& $venvPy -m src.snapshot
if ($LASTEXITCODE -ne 0) { Write-Host "`nLa exportación falló; pégale esta salida a Claude." -ForegroundColor Red; exit 1 }

Write-Host "`n=== Prueba: el tablero carga con la copia (sin MySQL) ===" -ForegroundColor Cyan
$env:PORK_DATA = "snapshot"
& $venvPy -m pytest tests/test_snapshot.py -q
$code = $LASTEXITCODE
Remove-Item Env:\PORK_DATA
if ($code -ne 0) { Write-Host "`nAlguna prueba falló; pégale esta salida a Claude." -ForegroundColor Red; exit 1 }

Write-Host "`nListo. Para publicarla, sube la carpeta a GitHub:" -ForegroundColor Green
Write-Host "  git add data/snapshot"
Write-Host "  git commit -m `"Copia pública de gold para el tablero en línea`""
Write-Host "  git push"
