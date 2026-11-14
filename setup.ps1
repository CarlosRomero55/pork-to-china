# setup.ps1 · Fase 1 · Pork to China
# Crea el entorno virtual, instala las librerías y verifica la configuración.
# Uso (en PowerShell, dentro de D:\pork-to-china):   .\setup.ps1
# Si Windows bloquea el script, ejecuta antes:       Set-ExecutionPolicy -Scope Process Bypass

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
Write-Host "=== Pork to China · setup ===" -ForegroundColor Cyan

# Función auxiliar: detiene el script si el último comando externo falló
function Assert-Ok([string]$paso) {
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`nERROR en: $paso (código $LASTEXITCODE). El script se detuvo; pégale esta salida a Claude." -ForegroundColor Red
        exit 1
    }
}

# 1) Detectar Python 3.12–3.14 (versiones con instaladores precompilados verificados)
$pyExe = "python"; $pyArgs = @()
foreach ($v in @("3.14", "3.13", "3.12")) {
    try {
        & py "-$v" --version *> $null
        if ($LASTEXITCODE -eq 0) { $pyExe = "py"; $pyArgs = @("-$v"); break }
    } catch {}
}
$ver = & $pyExe @pyArgs --version
Assert-Ok "detectar Python"
Write-Host "[1/5] Python detectado: $ver"

# 2) Crear el entorno virtual .venv (solo si no existe)
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    & $pyExe @pyArgs -m venv .venv
    Assert-Ok "crear .venv"
    Write-Host "[2/5] Entorno virtual creado en .venv"
} else {
    Write-Host "[2/5] .venv ya existe, se reutiliza"
}
$venvPy = ".\.venv\Scripts\python.exe"

# 3) Instalar dependencias SOLO desde instaladores precompilados (--only-binary):
#    si alguna librería no tiene wheel para tu Python, falla de inmediato en vez de intentar compilar.
& $venvPy -m pip install --upgrade pip --quiet
Assert-Ok "actualizar pip"
& $venvPy -m pip install -r requirements.txt --only-binary ":all:" --quiet
Assert-Ok "instalar librerías"
Write-Host "[3/5] Librerías instaladas"

# 4) Crear .env a partir de la plantilla si no existe (NO sobrescribe uno existente)
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "[4/5] Se creó .env desde .env.example -> COMPLETA tus credenciales con: notepad .env" -ForegroundColor Yellow
} else {
    Write-Host "[4/5] .env ya existe, no se toca"
}

# 5) Verificación: importar librerías clave y revisar la configuración
& $venvPy -c "import sys, pandas, sqlalchemy, pymysql, cryptography, comtradeapicall, numpy_financial, fastapi, pdfplumber; print('[5/5] Importaciones OK · Python', sys.version.split()[0], '· pandas', pandas.__version__, '· SQLAlchemy', sqlalchemy.__version__)"
Assert-Ok "importar librerías"
& $venvPy -m src.config
if ($LASTEXITCODE -ne 0) {
    Write-Host "`nFaltan credenciales en .env (normal la primera vez). Completa con: notepad .env  y vuelve a correr .\setup.ps1" -ForegroundColor Yellow
} else {
    Write-Host "`nTodo listo." -ForegroundColor Green
}
