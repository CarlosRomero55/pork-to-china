"""
gold_source.py · De dónde lee el tablero: MySQL (tu PC) o la copia pública en Parquet (la web)

Dos modos, con las MISMAS consultas SQL:
  - mysql     → pork_gold en tu MySQL, con el usuario de solo lectura (pork_bi). Es el modo de siempre.
  - snapshot  → los archivos de data/snapshot/ (exportados con .\\snapshot.ps1), consultados con DuckDB.
                Es lo que usa la app publicada en Streamlit Community Cloud, donde no hay MySQL.

Cómo se elige: la variable PORK_DATA (mysql | snapshot). Si no está, se usa mysql cuando hay credenciales
de solo lectura (BI_PASSWORD) y, si no las hay pero existe la copia, snapshot.

Por qué DuckDB: lee Parquet directo, entiende el mismo SQL estándar del tablero (CTE, funciones de ventana,
USING) y no necesita servidor. Solo cambian los parámetros (:nombre en MySQL → $nombre en DuckDB).
"""
from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

from src.config import ROOT_DIR

SNAPSHOT_DIR = ROOT_DIR / "data" / "snapshot"
GOLD = "pork_gold"

# Tablas y vistas de gold que lee el tablero (y la simulación What-If). La prueba test_snapshot.py
# revisa que esta lista cubra todo lo que el código consulta: si agregas una consulta nueva, súmala aquí.
GOLD_OBJECTS = (
    "dim_country", "dim_product", "dim_scenario",
    "fact_china_imports", "fact_landed_cost",
    "fact_scenario_result", "fact_scenario_cashflow", "fact_scenario_market",
    "fact_its_series", "fact_its_coef",
    "fact_mc_summary", "fact_mc_hist", "fact_mc_tornado",
    "fact_trigger",
    "v_scenario_params", "v_last_pipeline_run",
    "v_dash_china_balance", "v_dash_sam_yearly", "v_dash_supplier_monthly",
    "v_dash_province_pigs", "v_dash_sanitary", "v_dash_access_benchmark", "v_dash_policy_events",
)

_PARAM = re.compile(r"(?<![:\w]):([A-Za-z_]\w*)")


def mode() -> str:
    elegido = os.getenv("PORK_DATA", "").strip().lower()
    if elegido in ("mysql", "snapshot"):
        return elegido
    if os.getenv("BI_PASSWORD"):
        return "mysql"
    return "snapshot" if (SNAPSHOT_DIR / "manifest.json").exists() else "mysql"


def manifest() -> dict:
    """Qué contiene la copia: fecha de exportación, corrida del pipeline y filas por tabla."""
    f = SNAPSHOT_DIR / "manifest.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def to_duckdb(sql: str) -> str:
    """Convierte los parámetros :nombre (SQLAlchemy/MySQL) a $nombre (DuckDB), sin tocar textos entre comillas."""
    partes = re.split(r"('(?:[^']|'')*')", sql)       # las posiciones impares son literales '...'
    return "".join(p if i % 2 else _PARAM.sub(r"$\1", p) for i, p in enumerate(partes))


@lru_cache(maxsize=1)
def _duck():
    import duckdb

    if not (SNAPSHOT_DIR / "manifest.json").exists():
        raise FileNotFoundError("No hay copia en data/snapshot/: ejecuta .\\snapshot.ps1 en tu PC.")
    con = duckdb.connect(":memory:")
    con.execute(f"CREATE SCHEMA {GOLD}")
    for name in GOLD_OBJECTS:
        path = (SNAPSHOT_DIR / f"{name}.parquet").as_posix()
        con.execute(f"CREATE VIEW {GOLD}.{name} AS SELECT * FROM read_parquet('{path}')")
    return con


def _mysql_engine():
    from src.db import get_engine

    return get_engine("bi")


def read(sql: str, **params) -> pd.DataFrame:
    """Ejecuta una consulta de lectura sobre gold en el modo activo y devuelve un DataFrame."""
    if mode() == "snapshot":
        con = _duck().cursor()          # un cursor por consulta: seguro con los hilos de Streamlit
        return con.execute(to_duckdb(sql), params or None).df()
    from sqlalchemy import text

    with _mysql_engine().connect() as c:
        return pd.read_sql(text(sql), c, params=params)
