# validate.ps1 · Fase 6 · Pork to China
# Aplica migraciones, recarga silver con las marcas de calidad, valida las 11 reglas,
# regenera docs\data_quality_report.md y corre todas las pruebas.
# Uso (en PowerShell, dentro de D:\pork-to-china):   .\validate.ps1

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
$venvPy = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) { Write-Host "Primero ejecuta .\setup.ps1" -ForegroundColor Red; exit 1 }

& $venvPy -m src.migrate
if ($LASTEXITCODE -ne 0) { Write-Host "`nLas migraciones fallaron; pégale esta salida a Claude." -ForegroundColor Red; exit 1 }

& $venvPy -m src.harmonize | Select-String -Pattern "^\[1/4\]|^\[2/4\]|Todo listo"
if ($LASTEXITCODE -ne 0) { Write-Host "`nLa transformación falló; pégale esta salida a Claude." -ForegroundColor Red; exit 1 }

Write-Host ""
& $venvPy -m src.validate
if ($LASTEXITCODE -ne 0) { Write-Host "`nHay reglas con ERROR: los datos no pasan la validación. Pégale esta salida a Claude." -ForegroundColor Red; exit 1 }

Write-Host "`n=== Suite de pruebas (pytest) ===" -ForegroundColor Cyan
& $venvPy -m pytest tests -q
if ($LASTEXITCODE -ne 0) { Write-Host "`nAlguna prueba falló; pégale esta salida a Claude." -ForegroundColor Red; exit 1 }
Write-Host "`nFase 6 completa. Abre el reporte con:  notepad docs\data_quality_report.md" -ForegroundColor Green
