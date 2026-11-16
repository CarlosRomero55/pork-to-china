# api.ps1 · Fase 11 · Pork to China
# Levanta la API en tu PC y abre la documentación interactiva en el navegador.
# Uso (en PowerShell, dentro de D:\pork-to-china):   .\api.ps1        (Ctrl + C para detenerla)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
$env:PYTHONUTF8 = "1"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$venvPy = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) { Write-Host "Primero ejecuta .\setup.ps1" -ForegroundColor Red; exit 1 }

Write-Host "=== Pork to China · API ===" -ForegroundColor Cyan
Write-Host "Documentación:  http://127.0.0.1:8000/docs"
Write-Host "Ejemplo:        http://127.0.0.1:8000/tariffs?origin=ECU&hs=020649"
Write-Host "Para detenerla: Ctrl + C`n"
# Abre el navegador cuando el servidor ya está escuchando (3 segundos después)
Start-Job { Start-Sleep -Seconds 3; Start-Process "http://127.0.0.1:8000/docs" } | Out-Null
& $venvPy -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
