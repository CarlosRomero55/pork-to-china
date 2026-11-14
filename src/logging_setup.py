"""
logging_setup.py · Registro (logs) del proyecto.

Cada módulo pide su logger con get_logger(__name__). Los mensajes salen:
  - en consola (nivel LOG_LEVEL del .env), y
  - en logs/pipeline.log, que rota a los 5 MB y guarda 5 copias.
Así queda evidencia de cada ejecución sin llenar el disco.
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from src.config import LOGS_DIR, settings

_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_configured = False


def _configure_root() -> None:
    global _configured
    if _configured:
        return
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger("pork")
    root.setLevel(settings.log_level.upper())

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(levelname)-7s | %(message)s"))

    file_handler = RotatingFileHandler(
        LOGS_DIR / "pipeline.log", maxBytes=5_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(_FORMAT))

    root.addHandler(console)
    root.addHandler(file_handler)
    root.propagate = False
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Devuelve un logger hijo de 'pork' (ej. pork.src.extract_comtrade)."""
    _configure_root()
    return logging.getLogger(f"pork.{name}")
