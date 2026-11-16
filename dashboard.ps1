# dashboard.ps1 · Fase 12 · Pork to China
# Levanta el tablero de Streamlit y lo abre en el navegador.
# Uso (en PowerShell, dentro de D:\pork-to-china):   .\dashboard.ps1        (Ctrl + C para detenerlo)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
$env:PYTHONUTF8 = "1"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$venvPy = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) { Write-Host "Primero ejecuta .\setup.ps1" -ForegroundColor Red; exit 1 }

Write-Host "=== Pork to China · tablero ===" -ForegroundColor Cyan
Write-Host "Se abre en:     http://localhost:8501"
Write-Host "Para detenerlo: Ctrl + C`n"
& $venvPy -m streamlit run src\dashboard\app.py --server.port 8501 --server.headless false
