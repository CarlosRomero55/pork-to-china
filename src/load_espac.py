"""
Pork to China · Fase 13.2 · INEC ESPAC (tabulados Excel) → silver.province_pigs

Lee las tablas de ganado porcino del Excel de tabulados de la ESPAC que Carlos descarga del INEC
(data/raw/inec/Tabulados_ESPAC_<año>.xlsx):
  T57 · existencia y ventas por provincia
  T58 · existencia por variedad genética (de raza / mestizo / criollo)
  T59 · cerdos al año por provincia
Si el archivo no está (data/raw no se sube a GitHub), la etapa avisa y termina sin error.
"""
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

import openpyxl
import pandas as pd
from sqlalchemy import text

from src.config import ROOT_DIR
from src.db import SILVER, get_engine, track_batch, upsert_df
from src.logging_setup import get_logger

log = get_logger(__name__)
RAW_DIR = ROOT_DIR / "data" / "raw" / "inec"

# Código DPA del INEC por provincia continental (nombres sin tildes y en mayúsculas)
DPA = {"AZUAY": "01", "BOLIVAR": "02", "CANAR": "03", "CARCHI": "04", "COTOPAXI": "05", "CHIMBORAZO": "06",
       "EL ORO": "07", "ESMERALDAS": "08", "GUAYAS": "09", "IMBABURA": "10", "LOJA": "11", "LOS RIOS": "12",
       "MANABI": "13", "MORONA SANTIAGO": "14", "NAPO": "15", "PASTAZA": "16", "PICHINCHA": "17",
       "TUNGURAHUA": "18", "ZAMORA CHINCHIPE": "19", "SUCUMBIOS": "21", "ORELLANA": "22",
       "SANTO DOMINGO DE LOS TSACHILAS": "23", "SANTA ELENA": "24"}
# Nombre para mostrar (con tildes), por código DPA
DISPLAY = {"01": "Azuay", "02": "Bolívar", "03": "Cañar", "04": "Carchi", "05": "Cotopaxi", "06": "Chimborazo",
           "07": "El Oro", "08": "Esmeraldas", "09": "Guayas", "10": "Imbabura", "11": "Loja", "12": "Los Ríos",
           "13": "Manabí", "14": "Morona Santiago", "15": "Napo", "16": "Pastaza", "17": "Pichincha",
           "18": "Tungurahua", "19": "Zamora Chinchipe", "21": "Sucumbíos", "22": "Orellana",
           "23": "Santo Domingo de los Tsáchilas", "24": "Santa Elena"}
REGIONS = {"REGION SIERRA": "Sierra", "REGION COSTA": "Costa", "REGION AMAZONICA": "Amazonía"}


def norm(s: str) -> str:
    """Mayúsculas sin tildes ni espacios dobles: 'Región Amazónica' → 'REGION AMAZONICA'."""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().upper()


def province_rows(ws) -> dict[str, tuple[str, list[float]]]:
    """Filas de provincia de una hoja: {DPA: (región, [valores numéricos])}. Ignora totales y regiones."""
    out, region = {}, None
    for row in ws.iter_rows(values_only=True):
        cells = [c for c in row if c is not None and str(c).strip() != ""]
        if not cells:
            continue
        label = norm(cells[0])
        if label in REGIONS and len(cells) == 1:
            region = REGIONS[label]
            continue
        nums = [float(c) for c in cells[1:] if isinstance(c, (int, float))]
        if label in DPA and nums:
            out[DPA[label]] = (region, nums)
    return out


def read_espac(path: Path) -> pd.DataFrame:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    t57, t58, t59 = (province_rows(wb[t]) for t in ("T57", "T58", "T59"))
    rows = []
    for dpa, (region, v57) in t57.items():
        rows.append({
            "dpa_code": dpa,
            "province_name": DISPLAY[dpa],
            "region": region,
            "stock_head": round(v57[0]),
            "sales_q3_head": round(v57[3]),
            "breed_head": round(t58[dpa][1][1]),
            "pigs_per_year": round(t59[dpa][1][0]),
        })
    df = pd.DataFrame(rows).sort_values("dpa_code").reset_index(drop=True)
    if len(df) != len(DPA):
        missing = sorted(set(DPA.values()) - set(df["dpa_code"]))
        raise ValueError(f"El Excel no trae las {len(DPA)} provincias; faltan {missing}")
    return df


def latest_file() -> Path | None:
    files = sorted(RAW_DIR.glob("Tabulados_ESPAC_*.xlsx"))
    return files[-1] if files else None


def main() -> int:
    print("=== Pork to China · Fase 13.2 · INEC ESPAC: Excel → silver.province_pigs ===\n")
    path = latest_file()
    if path is None:
        print(f"AVISO: no hay Excel de la ESPAC en {RAW_DIR} (descárgalo del INEC). Se omite sin error.")
        return 0
    year = int(re.search(r"(\d{4})", path.name).group(1))
    df = read_espac(path)
    with track_batch("inec_espac", {"file": path.name, "year": year}) as b, get_engine("etl").begin() as conn:
        df["survey_year"] = year
        df["source_id"] = conn.execute(text(f"SELECT source_id FROM {SILVER}.source WHERE name='inec_espac'")).scalar()
        df["batch_id"] = b.batch_id
        b.rows_loaded = len(df)
        r = upsert_df(conn, df, SILVER, "province_pigs",
                      update_cols=["province_name", "region", "stock_head", "sales_q3_head", "breed_head",
                                   "pigs_per_year", "batch_id"])
    print(f"Archivo: {path.name} · año {year} · {len(df)} provincias · {r}")
    show = df.assign(pct=lambda d: (100 * d.pigs_per_year / d.pigs_per_year.sum()).round(1),
                     raza=lambda d: (100 * d.breed_head / d.stock_head).round(0))
    print("\nTop 8 por cerdos al año:")
    print(show.sort_values("pigs_per_year", ascending=False)
          .head(8)[["province_name", "region", "pigs_per_year", "pct", "stock_head", "raza"]].to_string(index=False))
    print(f"\nTotal: {df.pigs_per_year.sum():,} cerdos al año · {df.stock_head.sum():,} en existencia")
    return 0


if __name__ == "__main__":
    sys.exit(main())
