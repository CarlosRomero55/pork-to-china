"""
db.py · Capa de acceso a MySQL que usan todos los scripts del pipeline.

Funciones principales:
  get_engine(role)        conexión SQLAlchemy (role='etl' escribe; role='bi' solo lee gold)
  track_batch(...)        registra cada extracción en pork_bronze.extract_batch (ok / failed)
  save_raw_response(...)  guarda una respuesta de API intacta en bronze, sin duplicados (hash SHA-256)
  upsert_df(...)          inserta o actualiza un DataFrame por su clave única (carga idempotente)
  last_period(...)        "marca de agua" para la carga incremental: último mes cargado

Autoprueba (no deja datos):  python -m src.db
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from functools import lru_cache
from typing import Any, Iterator

import pandas as pd
from sqlalchemy import Connection, Engine, MetaData, Table, create_engine, text
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.engine import URL

from src.config import settings
from src.logging_setup import get_logger

log = get_logger(__name__)
BRONZE, SILVER, GOLD = settings.db_bronze, settings.db_silver, settings.db_gold


# ------------------------------------------------------------------ conexión
@lru_cache(maxsize=2)
def get_engine(role: str = "etl") -> Engine:
    """
    Crea (una sola vez) el motor de conexión.
    URL.create escapa la contraseña: funciona aunque tenga @, #, / u otros símbolos.
    pool_pre_ping evita el error "MySQL server has gone away" tras horas inactivo.
    """
    import os

    if role == "etl":
        user, pwd = settings.db_user, settings.db_password
    elif role == "bi":
        user, pwd = os.getenv("BI_USER", "pork_bi"), os.getenv("BI_PASSWORD", "")
    else:
        raise ValueError("role debe ser 'etl' o 'bi'")
    url = URL.create(
        "mysql+pymysql", username=user, password=pwd,
        host=settings.db_host, port=settings.db_port, query={"charset": "utf8mb4"},
    )
    return create_engine(url, pool_pre_ping=True, pool_recycle=3600, future=True)


# ------------------------------------------------------------------ lotes (auditoría)
@dataclass
class Batch:
    batch_id: int
    source_name: str
    rows_loaded: int = 0


@contextmanager
def track_batch(source_name: str, params: dict | None = None, engine: Engine | None = None) -> Iterator[Batch]:
    """
    Abre un lote en extract_batch con status='running' y lo cierra como 'ok' o 'failed'.
    Usa transacciones propias y cortas: aunque los datos del lote fallen y se reviertan,
    el registro del fallo QUEDA (es la auditoría).

        with track_batch("comtrade", {"reporter": 156}) as b:
            ...
            b.rows_loaded += n
    """
    engine = engine or get_engine("etl")
    with engine.begin() as conn:
        res = conn.execute(
            text(f"INSERT INTO {BRONZE}.extract_batch (source_name, params) VALUES (:s, :p)"),
            {"s": source_name, "p": json.dumps(params or {}, ensure_ascii=False, default=str)},
        )
        batch = Batch(batch_id=res.lastrowid, source_name=source_name)
    log.info("Lote %s abierto · fuente=%s · params=%s", batch.batch_id, source_name, params)
    try:
        yield batch
    except Exception as exc:
        with engine.begin() as conn:
            conn.execute(
                text(f"""UPDATE {BRONZE}.extract_batch
                         SET status='failed', finished_at=NOW(), rows_loaded=:n, error_msg=:e
                         WHERE batch_id=:b"""),
                {"n": batch.rows_loaded, "e": f"{type(exc).__name__}: {exc}"[:2000], "b": batch.batch_id},
            )
        log.error("Lote %s FALLÓ: %s", batch.batch_id, exc)
        raise
    else:
        with engine.begin() as conn:
            conn.execute(
                text(f"""UPDATE {BRONZE}.extract_batch
                         SET status='ok', finished_at=NOW(), rows_loaded=:n WHERE batch_id=:b"""),
                {"n": batch.rows_loaded, "b": batch.batch_id},
            )
        log.info("Lote %s OK · %s filas", batch.batch_id, batch.rows_loaded)


# ------------------------------------------------------------------ bronze
def payload_hash(payload: Any) -> str:
    """SHA-256 del JSON canónico (claves ordenadas): el mismo contenido da el mismo hash."""
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def save_raw_response(conn: Connection, batch_id: int, source_name: str, endpoint: str,
                      request_params: dict | None, payload: Any) -> tuple[int | None, bool]:
    """
    Guarda la respuesta cruda en bronze. Si ya existe una idéntica (mismo hash), no la duplica.
    Devuelve (raw_id, es_nueva).
    """
    h = payload_hash(payload)
    res = conn.execute(
        text(f"""INSERT IGNORE INTO {BRONZE}.raw_api_response
                 (batch_id, source_name, endpoint, request_params, payload, payload_hash)
                 VALUES (:b, :s, :e, :rp, :p, :h)"""),
        {"b": batch_id, "s": source_name, "e": endpoint,
         "rp": json.dumps(request_params or {}, ensure_ascii=False, default=str),
         "p": json.dumps(payload, ensure_ascii=False, default=str), "h": h},
    )
    if res.rowcount == 1:
        return res.lastrowid, True
    raw_id = conn.execute(
        text(f"SELECT raw_id FROM {BRONZE}.raw_api_response WHERE payload_hash=:h"), {"h": h}
    ).scalar()
    log.debug("Respuesta repetida (hash %s…), no se duplica", h[:10])
    return raw_id, False


# ------------------------------------------------------------------ upsert
def _clean(value: Any) -> Any:
    """Convierte NaN/NaT de pandas en NULL y tipos de numpy en tipos de Python."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if value is pd.NaT:
        return None
    if hasattr(value, "item"):  # numpy int64/float64
        value = value.item()
        if isinstance(value, float) and math.isnan(value):
            return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    return value


@lru_cache(maxsize=64)
def _reflect(schema: str, table: str, engine_id: int) -> Table:
    engine = get_engine("etl")
    return Table(table, MetaData(), schema=schema, autoload_with=engine)


@dataclass
class UpsertResult:
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0

    def __str__(self) -> str:
        return f"{self.inserted} nuevas · {self.updated} actualizadas · {self.unchanged} sin cambios"


def upsert_df(conn: Connection, df: pd.DataFrame, schema: str, table: str,
              update_cols: list[str] | None = None, chunk_size: int = 1000) -> UpsertResult:
    """
    INSERT ... ON DUPLICATE KEY UPDATE por lotes de chunk_size filas.
    - Si la fila no existe (según la PK o una clave UNIQUE) → se inserta.
    - Si existe y cambió algún valor de update_cols → se actualiza.
    - Si existe y es idéntica → no se toca.
    Correrlo dos veces con los mismos datos no duplica nada (idempotente).

    Conteo: las nuevas se miden con COUNT(*) antes/después; las actualizadas, con el
    "affected rows" de MySQL (ver comentario en el bucle).
    """
    result = UpsertResult()
    if df.empty:
        return result
    tbl = _reflect(schema, table, id(get_engine("etl")))
    unknown = set(df.columns) - set(tbl.columns.keys())
    if unknown:
        raise ValueError(f"Columnas que no existen en {schema}.{table}: {sorted(unknown)}")
    if update_cols is None:
        key_cols = {c.name for c in tbl.primary_key.columns}
        for idx in tbl.indexes:
            if idx.unique:
                key_cols |= {c.name for c in idx.columns}
        update_cols = [c for c in df.columns if c not in key_cols]

    records = [{k: _clean(v) for k, v in row.items()} for row in df.to_dict("records")]
    for start in range(0, len(records), chunk_size):
        chunk = records[start:start + chunk_size]
        stmt = mysql_insert(tbl).values(chunk)
        if update_cols:
            stmt = stmt.on_duplicate_key_update({c: stmt.inserted[c] for c in update_cols})
        else:
            stmt = stmt.prefix_with("IGNORE")
        # Para distinguir nuevas de actualizadas se cuenta antes/después
        before = conn.execute(text(f"SELECT COUNT(*) FROM `{schema}`.`{table}`")).scalar()
        affected = conn.execute(stmt).rowcount
        after = conn.execute(text(f"SELECT COUNT(*) FROM `{schema}`.`{table}`")).scalar()
        ins = after - before
        # SQLAlchemy conecta con CLIENT_FOUND_ROWS: MySQL cuenta 1 por fila nueva, 2 por
        # actualizada y 1 por fila idéntica → affected = len(chunk) + actualizadas.
        upd = max(affected - len(chunk), 0) if update_cols else 0
        result.inserted += ins
        result.updated += upd
        result.unchanged += len(chunk) - ins - upd
    log.info("Upsert %s.%s · %s", schema, table, result)
    return result


# ------------------------------------------------------------------ carga incremental
def last_period(conn: Connection, schema: str, table: str, date_col: str = "period",
                where: str | None = None, params: dict | None = None) -> date | None:
    """
    Último periodo cargado (marca de agua). El extractor pide solo desde ese mes en adelante.
    Ej.: last_period(conn, SILVER, "trade_flow", where="source_id = :s", params={"s": 1})
    """
    sql = f"SELECT MAX(`{date_col}`) FROM `{schema}`.`{table}`" + (f" WHERE {where}" if where else "")
    value = conn.execute(text(sql), params or {}).scalar()
    if isinstance(value, datetime):
        return value.date()
    return value


# ------------------------------------------------------------------ autoprueba
def selftest() -> int:
    """Prueba conexión, permisos, hash, upsert e incremental. Todo en una transacción que se revierte."""
    print("=== Pork to China · Fase 3 · autoprueba de db.py ===\n")
    ok = True
    eng = get_engine("etl")
    with eng.connect() as conn:
        version, user = conn.execute(text("SELECT VERSION(), CURRENT_USER()")).one()
        print(f"[1/5] Conectado a MySQL {version} como {user}")

    bi = get_engine("bi")
    with bi.connect() as conn:
        n = conn.execute(text(f"SELECT COUNT(*) FROM {GOLD}.dim_date")).scalar()
        print(f"[2/5] Usuario pork_bi lee gold: dim_date tiene {n} meses")

    with eng.connect() as conn:
        trans = conn.begin()
        try:
            # Hash: la misma respuesta (aunque cambie el orden de las claves) no se duplica
            batch_id = conn.execute(
                text(f"INSERT INTO {BRONZE}.extract_batch (source_name) VALUES ('selftest')")).lastrowid
            payload = {"data": [{"reporter": 156, "partner": 842, "value": 100}], "count": 1}
            same_reordered = {"count": 1, "data": [{"value": 100, "partner": 842, "reporter": 156}]}
            _, new1 = save_raw_response(conn, batch_id, "selftest", "/demo", {}, payload)
            _, new2 = save_raw_response(conn, batch_id, "selftest", "/demo", {}, same_reordered)
            good = new1 and not new2
            ok &= good
            print(f"[3/5] Bronze sin duplicados: 1ª vez nueva={new1}, 2ª vez nueva={new2}  {'OK' if good else 'ERROR'}")

            # Upsert: 2 filas de comercio de prueba (vísceras EE. UU. → China)
            ids = dict(conn.execute(text(f"SELECT iso3, country_id FROM {SILVER}.country "
                                          "WHERE iso3 IN ('CHN','USA','ESP')")).all())
            src = conn.execute(text(f"SELECT source_id FROM {SILVER}.source WHERE name='comtrade'")).scalar()
            df = pd.DataFrame({
                "reporter_id": [ids["CHN"], ids["CHN"]], "partner_id": [ids["USA"], ids["ESP"]],
                "hs_code": ["020649", "020649"], "period": [date(2025, 3, 1)] * 2, "flow_type": ["M", "M"],
                "net_weight_kg": [1000.0, float("nan")], "value_usd": [2150.0, 3000.0],
                "source_id": [src, src], "batch_id": [batch_id, batch_id],
            })
            r1 = upsert_df(conn, df, SILVER, "trade_flow", update_cols=["net_weight_kg", "value_usd", "batch_id"])
            r2 = upsert_df(conn, df, SILVER, "trade_flow", update_cols=["net_weight_kg", "value_usd", "batch_id"])
            df.loc[0, "value_usd"] = 2200.0  # la fuente corrige un valor
            r3 = upsert_df(conn, df, SILVER, "trade_flow", update_cols=["net_weight_kg", "value_usd", "batch_id"])
            good = (r1.inserted, r2.unchanged, r3.updated, r3.unchanged) == (2, 2, 1, 1)
            ok &= good
            print(f"[4/5] Upsert idempotente:\n      1ª carga: {r1}\n      2ª carga: {r2}\n"
                  f"      corrección: {r3}   {'OK' if good else 'ERROR'}")

            wm = last_period(conn, SILVER, "trade_flow", where="source_id = :s", params={"s": src})
            print(f"[5/5] Carga incremental: último periodo cargado = {wm}  {'OK' if wm else 'ERROR'}")
            ok &= wm is not None
        finally:
            trans.rollback()
            print("\n(Todo se revirtió: la autoprueba no deja datos en la base.)")

    print("\n" + ("Todo listo." if ok else "Hubo pruebas con ERROR; pégale esta salida a Claude."))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(selftest())
