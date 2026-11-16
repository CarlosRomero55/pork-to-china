"""
run_queries.py · Fase 9 · Consultas SQL de negocio

Corre cada consulta de sql/queries/ con el usuario de SOLO LECTURA (pork_bi: SELECT sobre gold)
y genera docs/queries.md con la pregunta, la técnica, la lectura y el resultado de cada una,
para que se pueda revisar en GitHub sin instalar nada.

Uso:  python -m src.run_queries            # todas
      python -m src.run_queries q05        # solo las que empiezan así
"""
from __future__ import annotations

import re
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from src.config import ROOT_DIR, SQL_DIR
from src.db import get_engine

QUERIES_DIR = SQL_DIR / "queries"
REPORT = ROOT_DIR / "docs" / "queries.md"
FIELDS = ("Pregunta", "Técnica", "Fuente", "Lectura")
MAX_ROWS = 30


def parse_header(sql: str) -> dict[str, str]:
    """Lee el encabezado de comentarios: '-- Campo: texto' y sus líneas de continuación."""
    meta, current = {}, None
    for line in sql.splitlines():
        if not line.startswith("--"):
            break
        body = line[2:].strip()
        m = re.match(rf"({'|'.join(FIELDS)}):\s*(.*)", body)
        if m:
            current = m.group(1)
            meta[current] = m.group(2)
        elif current and body:
            meta[current] += " " + body
    return meta


def load_queries(prefix: str = "") -> list[tuple[str, str, dict]]:
    files = sorted(QUERIES_DIR.glob(f"{prefix}*.sql"))
    return [(f.stem, f.read_text(encoding="utf-8"), parse_header(f.read_text(encoding="utf-8"))) for f in files]


def run(conn, sql: str) -> pd.DataFrame:
    res = conn.execute(text(sql))
    return pd.DataFrame(res.fetchall(), columns=list(res.keys()))


def fmt(v) -> str:
    """Formato español respetando los decimales que pidió la consulta (ROUND)."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    if isinstance(v, bool):
        return "sí" if v else "no"
    if isinstance(v, Decimal):
        decimals = max(-v.as_tuple().exponent, 0)
        txt = f"{v:,.{decimals}f}"
    elif isinstance(v, int):
        txt = f"{v:,}" if abs(v) >= 10000 else str(v)      # años y puestos sin separador
    elif isinstance(v, float):
        txt = f"{v:,.2f}"
    else:
        return str(v)
    return txt.replace(",", "_").replace(".", ",").replace("_", ".")


def md(df: pd.DataFrame) -> str:
    head = df.head(MAX_ROWS)
    lines = ["| " + " | ".join(map(str, df.columns)) + " |", "|" + "---|" * len(df.columns)]
    lines += ["| " + " | ".join(fmt(v) for v in row) + " |" for row in head.itertuples(index=False)]
    if len(df) > MAX_ROWS:
        lines.append(f"\n*… y {len(df) - MAX_ROWS} filas más (ver la consulta completa).*")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    prefix = (argv if argv is not None else sys.argv[1:] or [""])[0]
    queries = load_queries(prefix)
    if not queries:
        print(f"No hay consultas que empiecen con '{prefix}' en {QUERIES_DIR}")
        return 1
    pd.set_option("display.width", 180)
    print("=== Pork to China · Fase 9 · consultas de negocio (usuario de solo lectura) ===")
    out = ["# Consultas SQL de negocio", "",
           f"Generado por `src/run_queries.py` el {date.today():%Y-%m-%d} con el usuario de solo lectura "
           "`pork_bi` sobre `pork_gold`. Cada consulta está en `sql/queries/`.", ""]
    with get_engine("bi").connect() as conn:
        for name, sql, meta in queries:
            df = run(conn, sql)
            print(f"\n[{name}] {meta.get('Pregunta', '')}\n")
            print(df.head(MAX_ROWS).to_string(index=False))
            out += [f"## {name}", ""]
            out += [f"**{k}:** {meta[k]}  " for k in FIELDS if k in meta]
            out += ["", f"[Ver SQL](../sql/queries/{name}.sql) · {len(df)} filas", "", md(df), ""]
    if not prefix:
        REPORT.write_text("\n".join(out), encoding="utf-8")
        print(f"\nReporte: {REPORT.relative_to(ROOT_DIR)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
