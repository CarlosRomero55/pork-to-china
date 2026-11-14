"""
migrate.py · Aplica en orden las migraciones de sql/migrations/ que todavía no se aplicaron.

Cada archivo NNN_nombre.sql se ejecuta una sola vez y queda registrado en
pork_silver.schema_migration (nombre + hash + fecha). Si alguien edita una migración
ya aplicada, el hash no coincide y se avisa en lugar de reaplicarla en silencio.

Así la base evoluciona sin borrarse ni recrearse: es el mismo principio de Flyway o Alembic.
Uso:  python -m src.migrate
"""
from __future__ import annotations

import hashlib
import sys

from sqlalchemy import text

from src.config import SQL_DIR
from src.db import SILVER, get_engine
from src.db_setup import split_sql
from src.logging_setup import get_logger

log = get_logger(__name__)
MIGRATIONS_DIR = SQL_DIR / "migrations"


def migrate(engine=None) -> list[str]:
    engine = engine or get_engine("etl")
    applied_now = []
    with engine.begin() as conn:
        conn.execute(text(f"""CREATE TABLE IF NOT EXISTS {SILVER}.schema_migration (
            name VARCHAR(120) NOT NULL PRIMARY KEY,
            sha256 CHAR(64) NOT NULL,
            applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)"""))
        done = dict(conn.execute(text(f"SELECT name, sha256 FROM {SILVER}.schema_migration")).all())
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        sql = path.read_text(encoding="utf-8")
        digest = hashlib.sha256(sql.encode("utf-8")).hexdigest()
        if path.name in done:
            if done[path.name] != digest:
                log.warning("La migración %s cambió después de aplicarse; no se reaplica", path.name)
            continue
        # MySQL confirma solo los ALTER; el resto va en una transacción
        with engine.begin() as conn:
            for stmt in split_sql(sql):
                conn.execute(text(stmt))
            conn.execute(text(f"INSERT INTO {SILVER}.schema_migration (name, sha256) VALUES (:n, :h)"),
                         {"n": path.name, "h": digest})
        applied_now.append(path.name)
        log.info("Migración aplicada: %s", path.name)
    return applied_now


def main() -> int:
    applied = migrate()
    print("Migraciones aplicadas: " + (", ".join(applied) if applied else "ninguna pendiente"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
