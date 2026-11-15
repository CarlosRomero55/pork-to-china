"""
harmonize.py · Fase 5 · Comtrade: bronze → silver.trade_flow

Pasos:
  1. Lee de bronze la versión MÁS RECIENTE de cada consulta de Comtrade (bronze guarda todas).
  2. Limpia con clean.py y traduce códigos Comtrade → country_id del catálogo.
     Filas con países que no están en el catálogo van a CUARENTENA (se reportan, no se pierden).
  3. Carga con upsert (idempotente) separando la fuente:
       comtrade         = lo que reporta China (importaciones, CIF) y Ecuador (exportaciones)
       comtrade_mirror  = lo que reportan los exportadores sobre sus ventas a China (FOB)
  4. Reporte de calidad + conciliación directo vs espejo (2018–2024) + vista previa 2024 vs 2025.

Uso:  python -m src.harmonize
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
from sqlalchemy import text

from src.clean import flag_unit_value_outliers, parse_comtrade, quality_summary
from src.db import BRONZE, SILVER, get_engine, upsert_df
from src.logging_setup import get_logger

log = get_logger(__name__)
UPDATE_COLS = ["net_weight_kg", "value_usd", "quality_flag", "batch_id"]
CHINA = 156


def latest_comtrade_responses(conn):
    """
    Genera (batch_id, request_params, payload) · solo la última versión de cada consulta distinta.

    En 2 pasos a propósito: ordenar o agrupar filas que llevan el JSON completo (cientos de KB)
    agota el sort buffer de MySQL ("Out of sort memory"). Primero se obtienen solo los IDs
    (consulta liviana) y luego cada payload se lee por su clave primaria, uno a la vez.
    """
    ids = conn.execute(text(f"""
        SELECT MAX(raw_id) FROM {BRONZE}.raw_api_response
        WHERE source_name = 'comtrade'
        GROUP BY endpoint, payload_hash IS NOT NULL, CAST(request_params AS CHAR(2000))""")).scalars().all()
    for raw_id in sorted(ids):
        b, p, pl = conn.execute(text(f"SELECT batch_id, request_params, payload FROM {BRONZE}.raw_api_response "
                                     "WHERE raw_id = :i"), {"i": raw_id}).one()
        yield b, (json.loads(p) if isinstance(p, str) else p), (json.loads(pl) if isinstance(pl, str) else pl)


def ensure_sources(conn) -> dict[str, int]:
    conn.execute(text(f"""INSERT IGNORE INTO {SILVER}.source (name, publisher, url) VALUES
        ('comtrade','UN Statistics Division','https://comtradeplus.un.org'),
        ('comtrade_mirror','UN Statistics Division (datos espejo: exportadores → China)','https://comtradeplus.un.org')"""))
    conn.execute(text(f"""INSERT IGNORE INTO {SILVER}.country (iso3, comtrade_code, name_en, name_es) VALUES
        ('CHE',757,'Switzerland','Suiza'), ('CRI',188,'Costa Rica','Costa Rica')"""))
    return dict(conn.execute(text(f"SELECT name, source_id FROM {SILVER}.source "
                                  "WHERE name IN ('comtrade','comtrade_mirror')")).all())


def build_flows(conn) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (filas listas para silver, filas en cuarentena)."""
    sources = ensure_sources(conn)
    countries = dict(conn.execute(text(f"SELECT comtrade_code, country_id FROM {SILVER}.country")).all())
    frames = []
    for batch_id, params, payload in latest_comtrade_responses(conn):
        df = parse_comtrade(payload)
        if df.empty:
            continue
        is_mirror = str(params.get("partnerCode", "")) == str(CHINA)
        df["source"] = "comtrade_mirror" if is_mirror else "comtrade"
        df["batch_id"] = batch_id
        frames.append(df)
    if not frames:
        return pd.DataFrame(), pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df = flag_unit_value_outliers(df)

    df["reporter_id"] = df["reporter_code"].map(countries)
    df["partner_id"] = df["partner_code"].map(countries)
    df["source_id"] = df["source"].map(sources)
    bad = df["reporter_id"].isna() | df["partner_id"].isna()
    return df[~bad].copy(), df[bad].copy()


def quality_flags(df: pd.DataFrame) -> pd.Series:
    """Texto para la columna SET quality_flag (varias marcas separadas por coma, o NULL)."""
    parts = pd.DataFrame({
        "outlier_unit_value": df["is_outlier"].fillna(False),
        "missing_weight": df["net_weight_kg"].isna(),
        "weight_estimated_by_source": df["weight_estimated"].fillna(False),
    })
    flags = parts.apply(lambda r: ",".join(c for c in parts.columns if r[c]), axis=1)
    return flags.where(flags != "", None)


def load(conn, df: pd.DataFrame):
    df = df.assign(quality_flag=quality_flags(df))
    cols = ["reporter_id", "partner_id", "hs_code", "period", "flow_type",
            "net_weight_kg", "value_usd", "quality_flag", "source_id", "batch_id"]
    out = df[cols].astype({"reporter_id": int, "partner_id": int, "source_id": int, "batch_id": int})
    return upsert_df(conn, out, SILVER, "trade_flow", update_cols=UPDATE_COLS)


# ---------------------------------------------------------------- reportes
def iso_map(conn) -> dict[int, str]:
    return dict(conn.execute(text(f"SELECT comtrade_code, iso3 FROM {SILVER}.country")).all())


def reconciliation(df: pd.DataFrame, iso: dict[int, str]) -> pd.DataFrame:
    """
    2018–2024: lo que China dice haber importado de cada país (CIF) vs lo que ese país
    dice haberle exportado a China (FOB). Ratio > 1 es lo esperado (flete + seguro).
    """
    yrs = pd.to_datetime(df["period"]).dt.year
    direct = df[(df["source"] == "comtrade") & (df["reporter_code"] == CHINA) & (df["partner_code"] != 0) & (yrs <= 2024)]
    mirror = df[(df["source"] == "comtrade_mirror") & (yrs <= 2024)]
    d = direct.groupby("partner_code")[["value_usd", "net_weight_kg"]].sum()
    m = mirror.groupby("reporter_code")[["value_usd", "net_weight_kg"]].sum()
    r = d.join(m, lsuffix="_china", rsuffix="_exportador", how="inner")
    r["ratio_valor"] = r["value_usd_china"] / r["value_usd_exportador"]
    r["ratio_peso"] = r["net_weight_kg_china"] / r["net_weight_kg_exportador"]
    r.index = r.index.map(lambda c: iso.get(c, c))
    return r.sort_values("value_usd_china", ascending=False)


def preview_2024_vs_2025(df: pd.DataFrame, iso: dict[int, str]) -> pd.DataFrame:
    """Vista previa (datos espejo): toneladas enviadas a China por exportador, carne vs vísceras."""
    m = df[df["source"] == "comtrade_mirror"].copy()
    m["year"] = pd.to_datetime(m["period"]).dt.year
    m["grupo"] = np.where(m["hs_code"].str.startswith("0206"), "visceras",
                          np.where(m["hs_code"].str.startswith("0203"), "carne", "procesado"))
    m = m[m["year"].isin([2024, 2025]) & m["grupo"].isin(["carne", "visceras"])]
    t = m.pivot_table(index="reporter_code", columns=["grupo", "year"], values="net_weight_kg",
                      aggfunc="sum", fill_value=0) / 1000
    t.index = t.index.map(lambda c: iso.get(c, c))
    t[("total", "var_%")] = (t.xs(2025, axis=1, level=1).sum(axis=1) /
                             t.xs(2024, axis=1, level=1).sum(axis=1).replace(0, np.nan) - 1) * 100
    return t.sort_values(("total", "var_%"))


def main() -> int:
    pd.set_option("display.width", 160)
    pd.set_option("display.max_columns", 20)
    print("=== Pork to China · Fase 5 · Comtrade: bronze → silver ===\n")
    eng = get_engine("etl")
    with eng.begin() as conn:
        good, quarantine = build_flows(conn)
        if good.empty:
            print("No hay respuestas de Comtrade en bronze. Corre primero .\\extract.ps1")
            return 1
        result = load(conn, good)
        iso = iso_map(conn)

    print(f"[1/4] Carga a silver.trade_flow: {result}")
    by = good.assign(year=pd.to_datetime(good["period"]).dt.year).groupby(["source", "year"]).size().unstack(0).fillna(0).astype(int)
    print("      Filas por fuente y año:\n" + by.to_string().replace("\n", "\n      "))

    q = quality_summary(good)
    print(f"\n[2/4] Calidad: {q['rows']} filas · peso faltante {q['missing_weight']} · "
          f"peso estimado por la fuente {q['estimated_weight']} · USD/kg atípicos {q['outliers']}")
    if len(quarantine):
        codes = sorted(set(quarantine["reporter_code"]) | set(quarantine["partner_code"]))
        print(f"      Cuarentena: {len(quarantine)} filas con países fuera del catálogo (códigos {codes})")
    else:
        print("      Cuarentena: 0 filas (todos los países están en el catálogo)")
    out = good[good["is_outlier"]].nlargest(5, "value_usd")
    if len(out):
        out = out.assign(reporter=out["reporter_code"].map(iso), partner=out["partner_code"].map(iso))
        print("      Ejemplos de USD/kg atípicos (no se borran; se revisan en la Fase 6):")
        print("      " + out[["source", "reporter", "partner", "hs_code", "period", "net_weight_kg", "unit_value_usd_kg"]]
              .to_string(index=False).replace("\n", "\n      "))

    rec = reconciliation(good, iso)
    print("\n[3/4] Conciliación 2018–2024 · China (CIF) vs exportador (FOB):")
    show = rec[["value_usd_china", "value_usd_exportador", "ratio_valor", "ratio_peso"]].head(10).copy()
    show[["value_usd_china", "value_usd_exportador"]] = (show[["value_usd_china", "value_usd_exportador"]] / 1e6).round(0)
    show = show.rename(columns={"value_usd_china": "China_MUSD", "value_usd_exportador": "Export_MUSD"}).round(3)
    print("      " + show.to_string().replace("\n", "\n      "))
    w = rec["value_usd_china"]
    print(f"      Factor ponderado CIF/FOB (valor): {np.average(rec['ratio_valor'], weights=w):.3f} · "
          f"peso: {np.average(rec['ratio_peso'], weights=w):.3f}")

    pv = preview_2024_vs_2025(good, iso)
    print("\n[4/4] Vista previa (espejo) · toneladas enviadas a China, 2024 vs 2025:")
    print("      " + pv.round(1).to_string().replace("\n", "\n      "))
    print("\nTodo listo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
