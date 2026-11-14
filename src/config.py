"""
config.py · Configuración central del proyecto Pork to China.

Lee las variables del archivo .env (que solo existe en el PC de Carlos),
define las rutas del proyecto y valida que no falte nada antes de que
cualquier script se conecte a MySQL o a una API.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# --- Rutas del proyecto (relativas a la raíz, funcionan en Windows y Linux) ---
ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT_DIR / "data" / "raw"
DATA_PROCESSED = ROOT_DIR / "data" / "processed"
DATA_QUALITATIVE = ROOT_DIR / "data" / "qualitative"
LOGS_DIR = ROOT_DIR / "logs"
SQL_DIR = ROOT_DIR / "sql"

# Carga el .env de la raíz del proyecto (si no existe, las variables quedan vacías)
load_dotenv(ROOT_DIR / ".env")

# Variables obligatorias para la conexión a MySQL
REQUIRED_DB_VARS = ("DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD")


@dataclass(frozen=True)
class Settings:
    """Valores de configuración, todos leídos del entorno."""

    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: int = int(os.getenv("DB_PORT", "3306") or 3306)
    db_user: str = os.getenv("DB_USER", "")
    db_password: str = os.getenv("DB_PASSWORD", "")
    db_bronze: str = os.getenv("DB_BRONZE", "pork_bronze")
    db_silver: str = os.getenv("DB_SILVER", "pork_silver")
    db_gold: str = os.getenv("DB_GOLD", "pork_gold")
    comtrade_api_key: str = os.getenv("COMTRADE_API_KEY", "")
    usda_fas_api_key: str = os.getenv("USDA_FAS_API_KEY", "")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    start_year: int = int(os.getenv("START_YEAR", "2018") or 2018)


settings = Settings()


def missing_vars(names: tuple[str, ...] = REQUIRED_DB_VARS) -> list[str]:
    """Devuelve la lista de variables obligatorias que están vacías."""
    return [n for n in names if not os.getenv(n)]


def ensure_dirs() -> None:
    """Crea las carpetas de datos y logs si no existen."""
    for d in (DATA_RAW, DATA_PROCESSED, DATA_QUALITATIVE, LOGS_DIR):
        d.mkdir(parents=True, exist_ok=True)


def check() -> int:
    """
    Diagnóstico rápido: muestra qué está configurado SIN imprimir secretos.
    Devuelve 0 si todo está bien y 1 si falta algo.
    """
    ensure_dirs()
    print(f"Raíz del proyecto : {ROOT_DIR}")
    print(f".env encontrado   : {(ROOT_DIR / '.env').exists()}")
    faltan = missing_vars()
    for var in REQUIRED_DB_VARS:
        estado = "FALTA" if var in faltan else "OK"
        print(f"  {var:<12} {estado}")
    print(f"  COMTRADE_API_KEY {'OK' if settings.comtrade_api_key else 'vacía (se usará el modo sin llave, máx. 500 registros)'}")
    return 1 if faltan else 0


if __name__ == "__main__":
    sys.exit(check())
