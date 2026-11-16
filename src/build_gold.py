"""
build_gold.py · Fase 7 · silver → gold (esquema estrella)

Reconstruye gold completo en cada corrida (son decenas de miles de filas: tarda segundos
y gold nunca se desincroniza de silver):
  1. Dimensiones: dim_country, dim_product (upsert; dim_date ya viene del esquema).
  2. fact_china_imports: importaciones de China por mes × proveedor × línea HS,
     en dos bases que no se mezclan: directo (China, CIF) y espejo (exportadores, FOB).
  3. fact_tariff_applied: arancel total por mes × origen × línea HS, calculado a partir
     de las medidas SCD2 vigentes el día 15 de cada mes.
  4. fact_market_balance (USDA, miles de t CWE), fact_domestic_production y dim_scenario.
  5. Conciliación gold = silver y pruebas de negocio.

Uso:  python -m src.build_gold
"""
from __future__ import annotations

import sys
from datetime import date

import numpy as np
import pandas as pd
from sqlalchemy import text

from src.db import GOLD, SILVER, get_engine, upsert_df
from src.logging_setup import get_logger

log = get_logger(__name__)

GROUP_ES = {"meat": "Carne", "offal": "Vísceras", "processed": "Procesado"}
BLOC_BY_ISO3 = {"USA": "EE. UU.", "BRA": "Brasil", "CAN": "Canadá", "GBR": "Reino Unido",
                "CHL": "Chile", "ECU": "Ecuador"}
NOT_ORIGINS = {"CHN", "W00"}          # China no se exporta a sí misma; "Mundo" no es un origen
# Prueba de negocio: arancel total de China al cerdo de EE. UU. (020649), ya verificado (supuesto #7)
US_CHECKS = {20250101: 37, 20250401: 172, 20250701: 57, 20251101: 47}


# ---------------------------------------------------------------- dimensiones
def with_access(dim_country: pd.DataFrame, imports: pd.DataFrame, months: int = 24) -> pd.DataFrame:
    """
    Marca los países que le vendieron cerdo a China en los últimos `months` meses con datos.
    La ventana se mide dentro de cada base: el directo termina en 2024-12 y el espejo en 2026,
    así un país que solo aparece en el directo (p. ej. Costa Rica) no queda excluido por eso.
    """
    f = imports.assign(t=pd.to_numeric(imports["tonnes"], errors="coerce").fillna(0.0),
                       d=pd.to_datetime(imports["date_key"].astype(str)))
    sellers: set = set()
    for _, g in f.groupby("basis"):
        since = g["d"].max() - pd.DateOffset(months=months - 1)
        sellers |= set(g.loc[(g["d"] >= since) & (g["t"] > 0), "partner_key"])
    return dim_country.assign(exports_pork_to_china=dim_country["country_key"].isin(sellers))


def build_dims(conn) -> tuple[pd.DataFrame, pd.DataFrame]:
    countries = pd.read_sql(text(f"SELECT country_id, iso3, name_es FROM {SILVER}.country"), conn)
    eu_now = set(pd.read_sql(text(f"""
        SELECT m.country_id FROM {SILVER}.country_group_member m
        JOIN {SILVER}.country_group g ON g.group_id = m.group_id AND g.code = 'EU'
        WHERE CURDATE() BETWEEN m.valid_from AND m.valid_to"""), conn)["country_id"])
    countries = countries[countries["iso3"] != "W00"]
    dim_country = pd.DataFrame({
        "country_key": countries["country_id"],
        "iso3": countries["iso3"],
        "name_es": countries["name_es"],
        "supplier_bloc": [("UE" if cid in eu_now else BLOC_BY_ISO3.get(iso, "Otros"))
                          for cid, iso in zip(countries["country_id"], countries["iso3"])],
    })
    prods = pd.read_sql(text(f"""SELECT hs_code, product_group, description_es, is_ecuador_supply
                                 FROM {SILVER}.hs_product ORDER BY hs_code"""), conn)
    dim_product = pd.DataFrame({
        "product_key": range(1, len(prods) + 1),
        "hs_code": prods["hs_code"],
        "product_group_es": prods["product_group"].map(GROUP_ES),
        "description_es": prods["description_es"],
        "is_sam": prods["is_ecuador_supply"].astype(bool),   # SAM = líneas congeladas (kpis.md)
    })
    return dim_country, dim_product


# ---------------------------------------------------------------- importaciones de China
def shape_imports(flows: pd.DataFrame, product_keys: dict) -> pd.DataFrame:
    """flows: date, supplier_id, hs_code, basis, net_weight_kg, value_usd, quality_flag."""
    f = flows.copy()
    f["date_key"] = pd.to_datetime(f["date"]).dt.strftime("%Y%m%d").astype(int)
    f["tonnes"] = f["net_weight_kg"].astype(float) / 1000
    w = f["net_weight_kg"].astype(float)
    f["unit_value_usd_kg"] = np.where(w > 0, f["value_usd"].astype(float) / w.where(w > 0), np.nan).round(4)
    # Participación dentro de la MISMA base (directo o espejo), mes y línea HS
    tot = f.groupby(["date_key", "hs_code", "basis"])["tonnes"].transform("sum")
    f["share_pct"] = (f["tonnes"] / tot.where(tot > 0) * 100).round(4)
    f["is_outlier"] = f["quality_flag"].fillna("").str.contains("outlier_unit_value")
    return pd.DataFrame({
        "date_key": f["date_key"], "partner_key": f["supplier_id"],
        "product_key": f["hs_code"].map(product_keys), "basis": f["basis"],
        "tonnes": f["tonnes"].round(3), "value_usd": f["value_usd"].astype(float).round(2),
        "unit_value_usd_kg": f["unit_value_usd_kg"], "share_pct": f["share_pct"],
        "is_outlier": f["is_outlier"],
    }).replace({np.nan: None})


def read_flows(conn) -> pd.DataFrame:
    return pd.read_sql(text(f"""
        SELECT f.period AS date, f.partner_id AS supplier_id, f.hs_code, 'direct' AS basis,
               f.net_weight_kg, f.value_usd, f.quality_flag
        FROM {SILVER}.trade_flow f
        JOIN {SILVER}.source s ON s.source_id = f.source_id AND s.name = 'comtrade'
        JOIN {SILVER}.country r ON r.country_id = f.reporter_id AND r.iso3 = 'CHN'
        JOIN {SILVER}.country p ON p.country_id = f.partner_id AND p.iso3 <> 'W00'
        WHERE f.flow_type = 'M'
        UNION ALL
        SELECT f.period, f.reporter_id, f.hs_code, 'mirror', f.net_weight_kg, f.value_usd, f.quality_flag
        FROM {SILVER}.trade_flow f
        JOIN {SILVER}.source s ON s.source_id = f.source_id AND s.name = 'comtrade_mirror'
        JOIN {SILVER}.country p ON p.country_id = f.partner_id AND p.iso3 = 'CHN'
        WHERE f.flow_type = 'X'"""), conn)


# ---------------------------------------------------------------- arancel aplicado
def applied_tariffs(measures: pd.DataFrame, members: pd.DataFrame, months: pd.Series,
                    origins: list[int], hs_codes: list[str]) -> pd.DataFrame:
    """
    Calcula el arancel de China por mes × origen × línea HS.
    measures: hs_code, measure_type, rate_pct, valid_from, valid_to, target_id, target_group_id, target_company
    members:  group_id, country_id, valid_from, valid_to (pertenencia a bloques, p. ej. la UE)
    months:   primer día de cada mes; se evalúa la tasa vigente el día 15.
    """
    dates = pd.DataFrame({"month": pd.to_datetime(months)})
    dates["d"] = dates["month"] + pd.DateOffset(days=14)
    m = measures.copy()
    m["valid_from"], m["valid_to"] = pd.to_datetime(m["valid_from"]), pd.to_datetime(
        m["valid_to"].astype(str).replace("9999-12-31", "2262-04-11"))
    md = m.merge(dates, how="cross")
    md = md[(md["d"] >= md["valid_from"]) & (md["d"] <= md["valid_to"])]

    # Expandir cada medida a los orígenes que afecta
    to_all = md[md["target_id"].isna() & md["target_group_id"].isna()].merge(
        pd.DataFrame({"origin_id": origins}), how="cross")
    to_one = md[md["target_id"].notna()].assign(origin_id=lambda x: x["target_id"].astype(int))
    mem = members.rename(columns={"valid_from": "m_from", "valid_to": "m_to", "country_id": "origin_id"})
    mem["m_from"] = pd.to_datetime(mem["m_from"])
    mem["m_to"] = pd.to_datetime(mem["m_to"].astype(str).replace("9999-12-31", "2262-04-11"))
    to_grp = md[md["target_group_id"].notna()].merge(mem, left_on="target_group_id", right_on="group_id")
    to_grp = to_grp[(to_grp["d"] >= to_grp["m_from"]) & (to_grp["d"] <= to_grp["m_to"])]
    x = pd.concat([to_all, to_one, to_grp], ignore_index=True)
    x = x[x["origin_id"].isin(origins)]
    key = ["month", "origin_id", "hs_code"]

    mfn = x[x["measure_type"] == "mfn"].groupby(key)["rate_pct"].max().rename("mfn_pct")
    pref = x[x["measure_type"] == "preferential"].groupby(key)["rate_pct"].min().rename("preferential_pct")
    is_add = ~x["measure_type"].isin(["mfn", "preferential"]) & x["target_company"].isna()
    add = x[is_add].groupby(key)["rate_pct"].sum().rename("additional_pct")
    # Tasas por empresa: rango (mín–máx), nunca se suman entre sí
    comp = x[x["target_company"].notna()].groupby(key)["rate_pct"].agg(
        antidumping_min_pct="min", antidumping_max_pct="max")

    grid = pd.MultiIndex.from_product([dates["month"], origins, hs_codes], names=key).to_frame(index=False)
    out = (grid.merge(mfn, on=key, how="left").merge(pref, on=key, how="left")
               .merge(add, on=key, how="left").merge(comp, on=key, how="left"))
    if out["mfn_pct"].isna().any():
        faltan = out.loc[out["mfn_pct"].isna(), "hs_code"].unique()
        raise ValueError(f"Líneas HS sin NMF vigente: {list(faltan)}")
    out["additional_pct"] = out["additional_pct"].fillna(0)
    base = out["mfn_pct"] + out["additional_pct"]
    out["total_min_pct"] = base + out["antidumping_min_pct"].fillna(0)
    out["total_max_pct"] = base + out["antidumping_max_pct"].fillna(0)
    out["total_pref_pct"] = out["preferential_pct"] + out["additional_pct"]
    # Efectivo: el acuerdo reemplaza al NMF (no se suma); el antidumping se mantiene
    eff = out["preferential_pct"].fillna(out["mfn_pct"]) + out["additional_pct"]
    out["effective_min_pct"] = eff + out["antidumping_min_pct"].fillna(0)
    out["effective_max_pct"] = eff + out["antidumping_max_pct"].fillna(0)
    out["date_key"] = out["month"].dt.strftime("%Y%m%d").astype(int)
    return out.drop(columns="month")


# ---------------------------------------------------------------- balance, producción y escenarios
PSD_COLS = {"Production": "production_kt", "Imports": "imports_kt", "Exports": "exports_kt",
            "Domestic Consumption": "consumption_kt", "Ending Stocks": "ending_stocks_kt"}


def shape_balance(rows: pd.DataFrame, last_closed_year: int) -> pd.DataFrame:
    """rows (formato largo de silver): psd_code, name, country_id, market_year, attribute, value, released."""
    r = rows[rows["attribute"].isin(PSD_COLS)]
    wide = (r.pivot_table(index=["psd_code", "market_year"], columns="attribute", values="value", aggfunc="last")
             .rename(columns=PSD_COLS).reset_index())
    for c in PSD_COLS.values():
        if c not in wide.columns:
            wide[c] = np.nan
    info = r.groupby(["psd_code", "market_year"]).agg(area_name=("name", "first"), country_key=("country_id", "first"),
                                                      released=("released", "max")).reset_index()
    out = wide.merge(info, on=["psd_code", "market_year"])
    cons = out["consumption_kt"].where(out["consumption_kt"] > 0)
    out["import_share_pct"] = (out["imports_kt"] / cons * 100).round(2)
    out["self_sufficiency_pct"] = (out["production_kt"] / cons * 100).round(2)
    out["is_projection"] = out["market_year"] > last_closed_year
    cols = ["psd_code", "market_year", "area_name", "country_key", *PSD_COLS.values(),
            "import_share_pct", "self_sufficiency_pct", "is_projection", "released"]
    return out[cols].astype(object).where(out[cols].notna(), None)


def read_balance(conn) -> pd.DataFrame:
    df = pd.read_sql(text(f"""
        SELECT b.psd_code, c.name, c.country_id, b.market_year, b.attribute, b.value, b.released
        FROM {SILVER}.psd_balance b JOIN {SILVER}.psd_country c ON c.psd_code = b.psd_code
        WHERE b.unit LIKE '%CWE%'"""), conn)
    df["value"] = pd.to_numeric(df["value"])
    return df


def read_production_and_scenarios(conn) -> tuple[pd.DataFrame, pd.DataFrame]:
    prod = pd.read_sql(text(f"""
        SELECT p.country_id AS country_key, p.year, s.name AS source_name, p.production_t,
               p.is_estimate, p.notes
        FROM {SILVER}.country_production p JOIN {SILVER}.source s ON s.source_id = p.source_id"""), conn)
    prod["is_estimate"] = prod["is_estimate"].astype(bool)
    sc = pd.read_sql(text(f"""SELECT scenario_id AS scenario_key, code, trade_case, china_selfsuff, cert_year,
                                     description_es AS label_es FROM {SILVER}.scenario"""), conn)
    sc["cert_year"] = sc["cert_year"].astype(object).where(sc["cert_year"].notna(), None)
    return prod, sc


# ---------------------------------------------------------------- carga
def main() -> int:
    pd.set_option("display.width", 160)
    print("=== Pork to China · Fase 7 · silver → gold ===\n")
    with get_engine("etl").begin() as conn:
        dim_country, dim_product = build_dims(conn)
        pkeys = dict(zip(dim_product["hs_code"], dim_product["product_key"]))

        imports = shape_imports(read_flows(conn), pkeys)
        dim_country = with_access(dim_country, imports)

        months = pd.read_sql(text(f"SELECT date FROM {GOLD}.dim_date ORDER BY date_key"), conn)["date"]
        measures = pd.read_sql(text(f"""
            SELECT m.hs_code, m.measure_type, m.rate_pct, m.valid_from, m.valid_to,
                   m.target_id, m.target_group_id, m.target_company
            FROM {SILVER}.trade_measure m
            JOIN {SILVER}.country c ON c.country_id = m.imposing_id AND c.iso3 = 'CHN'"""), conn)
        members = pd.read_sql(text(f"SELECT group_id, country_id, valid_from, valid_to FROM {SILVER}.country_group_member"), conn)
        origins = dim_country.loc[~dim_country["iso3"].isin(NOT_ORIGINS), "country_key"].tolist()
        tariffs = applied_tariffs(measures, members, months, origins, list(pkeys))
        tariffs = tariffs.assign(origin_key=tariffs.pop("origin_id"),
                                 product_key=tariffs.pop("hs_code").map(pkeys)).replace({np.nan: None})

        balance = shape_balance(read_balance(conn), last_closed_year=date.today().year - 1)
        production, scenarios = read_production_and_scenarios(conn)

        # Reconstrucción completa: primero se vacían los hechos (dependen de las dimensiones)
        for t in ("fact_tariff_applied", "fact_china_imports", "fact_market_balance", "fact_domestic_production"):
            conn.execute(text(f"DELETE FROM {GOLD}.{t}"))
        upsert_df(conn, dim_country, GOLD, "dim_country", ["iso3", "name_es", "supplier_bloc", "exports_pork_to_china"])
        upsert_df(conn, dim_product, GOLD, "dim_product", ["hs_code", "product_group_es", "description_es", "is_sam"])
        r_imp = upsert_df(conn, imports, GOLD, "fact_china_imports", ["tonnes"])
        r_tar = upsert_df(conn, tariffs, GOLD, "fact_tariff_applied", ["mfn_pct"])
        upsert_df(conn, scenarios, GOLD, "dim_scenario", ["code", "trade_case", "china_selfsuff", "cert_year", "label_es"])
        r_bal = upsert_df(conn, balance, GOLD, "fact_market_balance", ["production_kt"])
        r_prod = upsert_df(conn, production, GOLD, "fact_domestic_production", ["production_t"])

        print(f"[1/5] Dimensiones: {len(dim_country)} países · {len(dim_product)} líneas HS "
              f"(SAM: {', '.join(dim_product.loc[dim_product['is_sam'], 'hs_code'])})\n"
              f"      Con acceso real (venden cerdo a China, últimos 24 meses): {int(dim_country['exports_pork_to_china'].sum())} países · "
              f"Ecuador: {'sí' if dim_country.loc[dim_country['iso3'] == 'ECU', 'exports_pork_to_china'].any() else 'no'}")
        print(f"[2/5] fact_china_imports: {r_imp.inserted:,} filas · fact_tariff_applied: {r_tar.inserted:,} filas "
              f"({len(months)} meses × {len(origins)} orígenes × {len(pkeys)} líneas)".replace(",", "."))
        print(f"      fact_market_balance: {r_bal.inserted} filas · fact_domestic_production: {r_prod.inserted} · "
              f"dim_scenario: {len(scenarios)} escenarios")

        ok = reconcile(conn)
        show_tariffs(conn)
        show_balance(conn)
    print("\nTodo listo." if ok else "\nLa conciliación falló: pégale esta salida a Claude.")
    return 0 if ok else 1


def reconcile(conn) -> bool:
    """Gold debe sumar lo mismo que silver y reproducir el arancel ya verificado a EE. UU."""
    print("\n[3/5] Conciliación gold = silver")
    silver = read_flows(conn).groupby("basis")["net_weight_kg"].sum().astype(float) / 1000
    gold = pd.read_sql(text(f"SELECT basis, SUM(tonnes) t FROM {GOLD}.fact_china_imports GROUP BY basis"),
                       conn).set_index("basis")["t"].astype(float)
    ok = True
    for b in ("direct", "mirror"):
        same = abs(silver.get(b, 0) - gold.get(b, 0)) < 1
        ok &= same
        print(f"      {b:<7} silver {silver.get(b, 0):>14,.0f} t · gold {gold.get(b, 0):>14,.0f} t  "
              f"{'OK' if same else 'DIFERENCIA'}".replace(",", "."))
    for label, sq, gq in [
        ("USDA producción (kt CWE)",
         f"SELECT SUM(value) FROM {SILVER}.psd_balance WHERE attribute='Production' AND unit LIKE '%CWE%'",
         f"SELECT SUM(production_kt) FROM {GOLD}.fact_market_balance"),
        ("Producción nacional (t)", f"SELECT SUM(production_t) FROM {SILVER}.country_production",
         f"SELECT SUM(production_t) FROM {GOLD}.fact_domestic_production"),
        ("Escenarios", f"SELECT COUNT(*) FROM {SILVER}.scenario", f"SELECT COUNT(*) FROM {GOLD}.dim_scenario"),
    ]:
        sv, gv = (float(conn.execute(text(q)).scalar() or 0) for q in (sq, gq))
        same = abs(sv - gv) < 1
        ok &= same
        print(f"      {label:<25} silver {sv:>12,.0f} · gold {gv:>12,.0f}  {'OK' if same else 'DIFERENCIA'}".replace(",", "."))
    got = dict(conn.execute(text(f"""
        SELECT t.date_key, t.total_min_pct FROM {GOLD}.fact_tariff_applied t
        JOIN {GOLD}.dim_country c ON c.country_key = t.origin_key AND c.iso3 = 'USA'
        JOIN {GOLD}.dim_product p ON p.product_key = t.product_key AND p.hs_code = '020649'
        WHERE t.date_key IN :keys""").bindparams(
        __import__("sqlalchemy").bindparam("keys", expanding=True)), {"keys": list(US_CHECKS)}).all())
    for k, exp in US_CHECKS.items():
        same = got.get(k) is not None and float(got[k]) == exp
        ok &= same
        print(f"      EE. UU. 020649 {str(k)[:4]}-{str(k)[4:6]}: {got.get(k)}% (esperado {exp}%)  {'OK' if same else 'DIFERENCIA'}")
    return ok


def show_tariffs(conn) -> None:
    today = date.today().replace(day=1).strftime("%Y%m%d")
    df = pd.read_sql(text(f"""
        SELECT c.name_es AS origen, p.hs_code AS hs, t.mfn_pct AS nmf, t.additional_pct AS adicional,
               CONCAT_WS('–', t.antidumping_min_pct, NULLIF(t.antidumping_max_pct, t.antidumping_min_pct)) AS antidumping,
               t.preferential_pct AS acuerdo,
               CONCAT_WS('–', t.effective_min_pct, NULLIF(t.effective_max_pct, t.effective_min_pct)) AS efectivo,
               IF(c.exports_pork_to_china, 'sí', 'NO') AS acceso
        FROM {GOLD}.fact_tariff_applied t
        JOIN {GOLD}.dim_country c ON c.country_key = t.origin_key
        JOIN {GOLD}.dim_product p ON p.product_key = t.product_key
        WHERE t.date_key = {today} AND p.hs_code = '020649'
          AND c.iso3 IN ('USA','CAN','ESP','DNK','BRA','CHL','ECU')
        ORDER BY t.effective_min_pct DESC"""), conn)
    print(f"\n[4/5] Arancel de China a las vísceras congeladas (020649) en {today[:4]}-{today[4:6]} (%)")
    print("      " + df.fillna("—").to_string(index=False).replace("\n", "\n      "))


def show_balance(conn) -> None:
    df = pd.read_sql(text(f"""
        SELECT market_year AS año, production_kt AS produccion, consumption_kt AS consumo, imports_kt AS importa,
               import_share_pct AS `import_%`, self_sufficiency_pct AS `autosuf_%`,
               IF(is_projection, 'proyección', 'cerrado') AS estado
        FROM {GOLD}.fact_market_balance WHERE psd_code = 'CH' ORDER BY market_year"""), conn)
    print("\n[5/5] Balance de cerdo de China (USDA, miles de t CWE)")
    print("      " + df.to_string(index=False).replace("\n", "\n      "))
    ec = pd.read_sql(text(f"""
        SELECT p.year AS año, p.source_name AS fuente, p.production_t AS toneladas,
               IF(p.is_estimate, 'estimado', 'dato') AS tipo
        FROM {GOLD}.fact_domestic_production p JOIN {GOLD}.dim_country c ON c.country_key = p.country_key
        WHERE c.iso3 = 'ECU' ORDER BY p.year, p.source_name"""), conn)
    print("\n      Producción de Ecuador (t)")
    print("      " + ec.to_string(index=False).replace("\n", "\n      "))


if __name__ == "__main__":
    sys.exit(main())
