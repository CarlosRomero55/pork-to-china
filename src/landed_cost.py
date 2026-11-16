"""
landed_cost.py · Fase 10.1 · Costo puesto en China (landed cost) por kg

    CIF     = (FOB + flete) × (1 + seguro)
    arancel = CIF × tasa efectiva            (China cobra el arancel sobre el valor CIF)
    landed  = CIF + arancel

El IVA chino (9%) se excluye a propósito: se cobra igual a todos sobre (CIF + arancel), así que no
cambia el orden de los proveedores (supuesto #5).

Preguntas que responde:
  1. Hoy, ¿cuánto le cuesta a un importador chino 1 kg de vísceras (020649) puesto en China,
     según de dónde venga?
  2. ¿Qué precio FOB MÁXIMO podría cobrar Ecuador para igualar en destino a cada competidor?
  3. ¿Cambia la conclusión si el flete está en su mínimo o en su máximo?

Datos: precio FOB real de cada proveedor (gold, espejo 2025), arancel efectivo vigente
(gold.fact_tariff_applied) y supuestos versionados (silver.assumption, mín · base · máx).

Uso:  python -m src.landed_cost
"""
from __future__ import annotations

import sys
from dataclasses import dataclass

import pandas as pd
from sqlalchemy import text

from src.config import ROOT_DIR
from src.db import GOLD, SILVER, get_engine

REPORT = ROOT_DIR / "docs" / "landed_cost.md"
HS = ("020649", "020329")                  # vísceras congeladas y carne congelada (el SAM principal)
COMPETITORS = ("CHL", "BRA", "ESP", "DNK", "USA", "CAN")
ROUTE = {"ECU": "pacific", "CHL": "pacific", "PER": "pacific", "BRA": "brazil",
         "USA": "north_america", "CAN": "north_america", "MEX": "north_america"}   # resto de Europa → europe


@dataclass(frozen=True)
class Landed:
    fob: float
    freight: float
    insurance: float
    cif: float
    duty_pct: float
    duty: float
    landed: float


def landed_cost(fob: float, freight_kg: float, insurance_pct: float, duty_pct: float) -> Landed:
    """Costo puesto en China por kg. insurance_pct y duty_pct en porcentaje (0,3 = 0,3%)."""
    base = fob + freight_kg
    cif = base * (1 + insurance_pct / 100)
    duty = cif * duty_pct / 100
    return Landed(fob, freight_kg, cif - base, cif, duty_pct, duty, cif + duty)


def max_fob_to_match(target_landed: float, freight_kg: float, insurance_pct: float, duty_pct: float) -> float:
    """Inverso de landed_cost: el FOB con el que se iguala `target_landed` en destino."""
    return target_landed / ((1 + insurance_pct / 100) * (1 + duty_pct / 100)) - freight_kg


def route_of(iso3: str) -> str:
    return ROUTE.get(iso3, "europe")


# ---------------------------------------------------------------- lectura
def read_assumptions(conn) -> pd.DataFrame:
    """Última versión de cada supuesto (mín · base · máx)."""
    return pd.read_sql(text(f"""
        SELECT a.name, a.value_min AS min, a.value_base AS base, a.value_max AS max, a.version
        FROM {SILVER}.assumption a
        JOIN (SELECT name, MAX(version) v FROM {SILVER}.assumption GROUP BY name) last
          ON last.name = a.name AND last.v = a.version"""), conn).set_index("name").astype(
        {"min": float, "base": float, "max": float})


def read_market(conn) -> pd.DataFrame:
    """FOB 2025 por proveedor y línea (espejo, sin atípicos) + arancel efectivo vigente + acceso."""
    df = pd.read_sql(text(f"""
        WITH fob AS (
          SELECT c.iso3, p.hs_code, SUM(f.value_usd) / (1000 * SUM(f.tonnes)) AS fob_usd_kg, SUM(f.tonnes) AS tonnes
          FROM {GOLD}.fact_china_imports f
          JOIN {GOLD}.dim_country c ON c.country_key = f.partner_key
          JOIN {GOLD}.dim_product p ON p.product_key = f.product_key
          WHERE f.basis = 'mirror' AND f.date_key BETWEEN 20250101 AND 20251201
            AND NOT f.is_outlier AND f.tonnes > 0
          GROUP BY c.iso3, p.hs_code
        ),
        tariff AS (
          SELECT c.iso3, c.name_es, c.exports_pork_to_china AS has_access, p.hs_code,
                 t.mfn_pct, t.preferential_pct, t.effective_min_pct, t.effective_max_pct
          FROM {GOLD}.fact_tariff_applied t
          JOIN {GOLD}.dim_country c ON c.country_key = t.origin_key
          JOIN {GOLD}.dim_product p ON p.product_key = t.product_key
          WHERE t.date_key = (SELECT MAX(date_key) FROM {GOLD}.dim_date WHERE date <= CURDATE())
        )
        SELECT t.*, fob.fob_usd_kg, fob.tonnes
        FROM tariff t LEFT JOIN fob ON fob.iso3 = t.iso3 AND fob.hs_code = t.hs_code"""), conn)
    return df[df["hs_code"].isin(HS)]


# ---------------------------------------------------------------- modelo
def build(market: pd.DataFrame, a: pd.DataFrame, level: str = "base") -> pd.DataFrame:
    """Tabla de costo puesto en China. `level` = min · base · max para flete, carga y seguro."""
    payload_kg = a.loc["reefer_payload_t", {"min": "max", "base": "base", "max": "min"}[level]] * 1000
    insurance = a.loc["cargo_insurance_pct", level]
    # Ecuador no tiene historia de precio: es tomador de precio y vende al FOB de Chile de CADA línea
    chile_fob = market[market["iso3"] == "CHL"].set_index("hs_code")["fob_usd_kg"].astype(float).to_dict()
    rows = []
    for r in market.itertuples():
        if r.iso3 not in COMPETITORS + ("ECU",):
            continue
        freight_kg = a.loc[f"freight_reefer40_{route_of(r.iso3)}", level] / payload_kg
        cases = []
        if r.iso3 == "ECU":
            ec_fob = chile_fob.get(r.hs_code, a.loc["ecuador_fob_usd_kg_offal", "base"])
            cases = [("Ecuador (NMF)", ec_fob, r.mfn_pct, r.mfn_pct),
                     ("Ecuador (con acuerdo)", ec_fob, r.effective_min_pct, r.effective_min_pct)]
        elif pd.notna(r.fob_usd_kg):
            cases = [(r.name_es, float(r.fob_usd_kg), r.effective_min_pct, r.effective_max_pct)]
        for label, fob, dmin, dmax in cases:
            lo = landed_cost(fob, freight_kg, insurance, float(dmin))
            hi = landed_cost(fob, freight_kg, insurance, float(dmax))
            rows.append(dict(hs=r.hs_code, proveedor=label, iso3=r.iso3, acceso="sí" if r.has_access else "NO",
                             fob=round(fob, 2), flete=round(freight_kg, 3), seguro=round(lo.insurance, 3),
                             cif=round(lo.cif, 2), arancel_pct=f"{float(dmin):g}" + (f"–{float(dmax):g}" if dmax != dmin else ""),
                             landed_min=round(lo.landed, 2), landed_max=round(hi.landed, 2)))
    out = pd.DataFrame(rows)
    best = out[out["acceso"] == "sí"].groupby("hs")["landed_min"].min()
    out["vs_mejor"] = (out["landed_min"] - out["hs"].map(best)).round(2)
    return out.sort_values(["hs", "landed_min"]).reset_index(drop=True)


def max_fob_table(market: pd.DataFrame, a: pd.DataFrame, table: pd.DataFrame, hs: str = "020649") -> pd.DataFrame:
    """FOB máximo de Ecuador (con acuerdo) para igualar en destino a cada competidor con acceso."""
    ec = market[(market["iso3"] == "ECU") & (market["hs_code"] == hs)].iloc[0]
    rows = []
    for level in ("min", "base", "max"):
        payload_kg = a.loc["reefer_payload_t", {"min": "max", "base": "base", "max": "min"}[level]] * 1000
        fr = a.loc["freight_reefer40_pacific", level] / payload_kg
        ins = a.loc["cargo_insurance_pct", level]
        t = table[(table["hs"] == hs) & (table["acceso"] == "sí")]
        for r in t.itertuples():
            rows.append(dict(competidor=r.proveedor, landed=r.landed_min, flete=level,
                             fob_max=round(max_fob_to_match(r.landed_min, fr, ins, float(ec.effective_min_pct)), 2)))
    piv = pd.DataFrame(rows).pivot_table(index=["competidor", "landed"], columns="flete", values="fob_max")
    return piv[["min", "base", "max"]].reset_index().sort_values("landed").rename(
        columns={"landed": "landed_competidor", "min": "fob_max_flete_bajo", "base": "fob_max_base",
                 "max": "fob_max_flete_alto"})


def sensitivity(market: pd.DataFrame, a: pd.DataFrame) -> pd.DataFrame:
    """¿Cambia el orden de proveedores si flete, carga y seguro están en su mínimo o su máximo?"""
    ranks = {}
    for level in ("min", "base", "max"):
        t = build(market, a, level)
        t = t[t["hs"] == "020649"]
        ranks[f"puesto_{level}"] = t.set_index("proveedor")["landed_min"].rank(method="min").astype(int)
        ranks[f"landed_{level}"] = t.set_index("proveedor")["landed_min"]
    return pd.DataFrame(ranks).sort_values("landed_base")


# ---------------------------------------------------------------- reporte
def _md(df: pd.DataFrame) -> str:
    fmt = lambda v: (f"{v:,.3f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)) \
        .replace(",", "_").replace(".", ",").replace("_", ".")
    lines = ["| " + " | ".join(map(str, df.columns)) + " |", "|" + "---|" * len(df.columns)]
    return "\n".join(lines + ["| " + " | ".join(fmt(v) for v in r) + " |" for r in df.itertuples(index=False)])


def main() -> int:
    pd.set_option("display.width", 180)
    with get_engine("etl").connect() as conn:
        a, market = read_assumptions(conn), read_market(conn)
    table = build(market, a)
    fobmax = max_fob_table(market, a, table)
    sens = sensitivity(market, a)
    print("=== Pork to China · Fase 10.1 · costo puesto en China (USD/kg, sin IVA) ===\n")
    for hs, name in (("020649", "Vísceras congeladas"), ("020329", "Carne congelada")):
        print(f"[{hs}] {name}")
        print(table[table["hs"] == hs].drop(columns=["hs", "iso3"]).to_string(index=False), "\n")
    print("FOB máximo de Ecuador (con acuerdo) para igualar en destino a cada competidor · 020649")
    print(fobmax.to_string(index=False), "\n")
    print("Sensibilidad al flete · 020649 (puesto de cada proveedor por costo en destino)")
    print(sens.to_string(), "\n")
    stable = (sens["puesto_min"] == sens["puesto_base"]).all() and (sens["puesto_max"] == sens["puesto_base"]).all()
    print("El orden de proveedores " + ("NO cambia" if stable else "SÍ cambia") + " con el flete en su mínimo o máximo.")

    REPORT.write_text("\n".join([
        "# Costo puesto en China (landed cost)", "",
        "Generado por `src/landed_cost.py`. USD por kg, sin IVA (igual para todos). FOB real 2025 (espejo); "
        "arancel efectivo vigente; flete, carga y seguro según `silver.assumption` (mín · base · máx).", "",
        "## Vísceras congeladas (020649)", "", _md(table[table["hs"] == "020649"].drop(columns=["hs", "iso3"])), "",
        "## Carne congelada (020329)", "", _md(table[table["hs"] == "020329"].drop(columns=["hs", "iso3"])), "",
        "## FOB máximo de Ecuador para igualar en destino (020649, con acuerdo)", "", _md(fobmax), "",
        "## Sensibilidad al flete (020649)", "", _md(sens.reset_index()), "",
        f"El orden de proveedores {'no cambia' if stable else 'cambia'} con el flete en su mínimo o máximo.", ""]),
        encoding="utf-8")
    print(f"\nReporte: {REPORT.relative_to(ROOT_DIR)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
