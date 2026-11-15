"""
harmonize_psd.py · Fase 4.3b · USDA PSD: bronze (ZIP registrado) → silver.psd_balance

Pasos:
  1. Toma el ZIP más reciente de USDA registrado en pork_bronze.raw_file.
  2. Filtra carne de cerdo y años comerciales desde START_YEAR (2018).
  3. Traduce los códigos propios de USDA (CH, AS, E4...) al catálogo de países / bloques.
     Los países que no están en el catálogo se conservan con country_id NULL (no se descartan).
  4. Carga con upsert (idempotente) y muestra un resumen.

Uso:  python -m src.harmonize_psd
"""
from __future__ import annotations

import sys

import pandas as pd
from sqlalchemy import text

from src.config import ROOT_DIR, settings
from src.db import BRONZE, SILVER, get_engine, upsert_df
from src.extract_psd import read_pork_from_zip
from src.logging_setup import get_logger

log = get_logger(__name__)

# Códigos de USDA FAS → ISO3 del catálogo. Explícito a propósito: USDA usa códigos propios
# que confunden (AS = Australia y no Austria; AU = Austria; CI = Chile; EI = Irlanda; RS = Rusia).
PSD_TO_ISO3 = {
    "CH": "CHN", "EC": "ECU", "US": "USA", "CA": "CAN", "MX": "MEX", "BR": "BRA", "AR": "ARG",
    "CI": "CHL", "CO": "COL", "CS": "CRI", "UK": "GBR", "RS": "RUS", "VM": "VNM", "RP": "PHL",
    "KS": "KOR", "JA": "JPN", "AS": "AUS", "NZ": "NZL", "SZ": "CHE", "HK": "HKG",
    "AU": "AUT", "BU": "BGR", "HR": "HRV", "EZ": "CZE", "DA": "DNK", "EN": "EST", "FI": "FIN",
    "FR": "FRA", "GM": "DEU", "GR": "GRC", "HU": "HUN", "EI": "IRL", "IT": "ITA", "LG": "LVA",
    "LH": "LTU", "NL": "NLD", "PL": "POL", "PO": "PRT", "RO": "ROU", "SP": "ESP", "SW": "SWE",
}
PSD_TO_GROUP = {"E4": "EU"}       # agregado Unión Europea
KEY_ATTRS = ["Production", "Imports", "Exports", "Domestic Consumption"]


def latest_zip(conn):
    row = conn.execute(text(f"""
        SELECT file_id, batch_id, stored_path FROM {BRONZE}.raw_file
        WHERE source_name = 'usda_psd' ORDER BY file_id DESC LIMIT 1""")).first()
    if row is None:
        raise SystemExit("No hay archivos de USDA en bronze. Corre primero .\\psd.ps1")
    path = ROOT_DIR / row.stored_path
    if not path.exists():
        raise SystemExit(f"El archivo registrado no está en disco: {path}. Corre .\\psd.ps1 de nuevo")
    return row.batch_id, path


def build(conn, start_year: int) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    batch_id, path = latest_zip(conn)
    raw = read_pork_from_zip(path.read_bytes())
    raw["market_year"] = pd.to_numeric(raw["marketyear"], errors="coerce").astype("Int64")
    ec_years = raw.loc[raw["countrycode"] == "EC", "market_year"]
    info = {"ecuador_last_year": int(ec_years.max()) if len(ec_years) else None}
    raw = raw[raw["market_year"] >= start_year].copy()

    iso = dict(conn.execute(text(f"SELECT iso3, country_id FROM {SILVER}.country")).all())
    groups = dict(conn.execute(text(f"SELECT code, group_id FROM {SILVER}.country_group")).all())
    countries = raw.drop_duplicates("countrycode")[["countrycode", "countryname"]].rename(
        columns={"countrycode": "psd_code", "countryname": "name"})
    countries["country_id"] = countries["psd_code"].map(PSD_TO_ISO3).map(iso)
    countries["country_group_id"] = countries["psd_code"].map(PSD_TO_GROUP).map(groups)

    src = conn.execute(text(f"SELECT source_id FROM {SILVER}.source WHERE name='usda_psd'")).scalar()
    balance = pd.DataFrame({
        "psd_code": raw["countrycode"],
        "market_year": raw["market_year"].astype(int),
        "attribute": raw["attributedescription"],
        "value": pd.to_numeric(raw["value"], errors="coerce"),
        "unit": raw["unitdescription"],
        "released": raw["calendaryear"].str.cat(raw["month"].str.zfill(2), sep="-"),
        "source_id": src,
        "batch_id": batch_id,
    })
    return countries, balance, info


def main() -> int:
    pd.set_option("display.width", 160)
    print("=== Pork to China · Fase 4.3b · USDA PSD: bronze → silver ===\n")
    with get_engine("etl").begin() as conn:
        countries, balance, info = build(conn, settings.start_year)
        r1 = upsert_df(conn, countries, SILVER, "psd_country", update_cols=["name", "country_id", "country_group_id"])
        r2 = upsert_df(conn, balance, SILVER, "psd_balance", update_cols=["value", "unit", "released", "batch_id"])
    print(f"[1/3] psd_country: {r1}")
    print(f"      psd_balance: {r2}  ({balance['market_year'].min()}–{balance['market_year'].max()})")

    mapped = countries["country_id"].notna() | countries["country_group_id"].notna()
    print(f"\n[2/3] Países: {len(countries)} · vinculados al catálogo {mapped.sum()} · "
          f"solo en USDA {(~mapped).sum()} (se conservan)")
    if (countries["psd_code"] == "EC").any():
        print("      Ecuador en USDA: sí (EC)")
    else:
        last = info["ecuador_last_year"]
        print(f"      Ecuador en USDA: no desde {settings.start_year}" +
              (f" (USDA lo siguió hasta {last}); su producción vendrá de FAOSTAT/ASPE" if last else ""))

    key = balance[balance["attribute"].isin(KEY_ATTRS) & balance["psd_code"].isin(["CH", "EC", "BR", "US", "E4"])]
    piv = key.pivot_table(index=["psd_code", "market_year"], columns="attribute", values="value", aggfunc="last")
    piv = piv[[c for c in KEY_ATTRS if c in piv.columns]]
    yrs = [y for y in (2024, 2025, 2026, 2027) if y in piv.index.get_level_values(1)]
    print("\n[3/3] Balance (miles de t CWE) · " + ", ".join(str(y) for y in yrs))
    print("      " + piv.loc[(slice(None), yrs), :].round(0).to_string().replace("\n", "\n      "))
    print("\nTodo listo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
