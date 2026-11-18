"""
snapshot.py · Exporta la copia pública de gold para el tablero en línea

Lee de pork_gold, con el usuario de SOLO LECTURA, las tablas y vistas que usa el tablero (gold_source.GOLD_OBJECTS)
y las guarda en data/snapshot/ como Parquet, junto con manifest.json (fecha, última corrida y filas por tabla).

Todo lo que se exporta son datos públicos ya agregados (comercio, aranceles, supuestos y resultados de los modelos):
no hay credenciales ni datos personales. Por eso data/snapshot/ sí se sube a GitHub.

Uso (en tu PC, después de .\\pipeline.ps1):   .\\snapshot.ps1      (o python -m src.snapshot)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import text

from src.db import get_engine
from src.gold_source import GOLD, GOLD_OBJECTS, SNAPSHOT_DIR


def _limpiar(df: pd.DataFrame) -> pd.DataFrame:
    """MySQL devuelve DECIMAL como objetos Decimal: se guardan como float para que Parquet y DuckDB los lean igual."""
    for col in df.columns:
        if df[col].dtype == object and len(df) and df[col].map(lambda v: hasattr(v, "as_tuple")).any():
            df[col] = df[col].astype(float)
    return df


def exportar() -> dict:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    filas: dict[str, int] = {}
    with get_engine("bi").connect() as c:
        for name in GOLD_OBJECTS:
            df = _limpiar(pd.read_sql(text(f"SELECT * FROM {GOLD}.{name}"), c))
            df.to_parquet(SNAPSHOT_DIR / f"{name}.parquet", index=False)
            filas[name] = len(df)
            print(f"  {name:<28} {len(df):>8,} filas")
        corrida = c.execute(text(f"SELECT run_id, finished_at, status FROM {GOLD}.v_last_pipeline_run")).first()
    datos = {
        "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pipeline_run": None if corrida is None else {
            "run_id": corrida[0], "finished_at": str(corrida[1]), "status": corrida[2]},
        "rows": filas,
    }
    (SNAPSHOT_DIR / "manifest.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return datos


def main() -> int:
    print(f"Exportando {len(GOLD_OBJECTS)} tablas y vistas de {GOLD} a {SNAPSHOT_DIR} …")
    datos = exportar()
    vacias = [n for n, k in datos["rows"].items() if k == 0]
    if datos["rows"].get("fact_scenario_result", 0) == 0:
        print("\nGold está vacío: corre primero .\\pipeline.ps1 y vuelve a exportar.")
        return 1
    total = sum(datos["rows"].values())
    print(f"\nListo: {total:,} filas en {len(datos['rows'])} archivos.")
    if vacias:
        print("Aviso: sin filas en " + ", ".join(vacias))
    print("Siguiente paso: sube data/snapshot/ a GitHub (el script snapshot.ps1 te muestra los comandos).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
