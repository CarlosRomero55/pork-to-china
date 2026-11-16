"""
scenarios.py · Fase 10.2 · Mercado por escenario (TAM–SAM–SOM) y costo puesto en China por escenario

Para cada uno de los 24 escenarios y cada año del proyecto (1 = 2027 … 10 = 2036):

  TAM   = importaciones chinas de cerdo (12 líneas HS; espejo 2025) × índice de mercado
  SAM   = carne y vísceras congeladas (líneas SAM; espejo 2025) × índice de mercado
          índice: 2026–2027 = proyección de USDA (importaciones vs 2025); desde 2028, la tendencia del
          escenario (autosuficiencia china al alza −3%/año · a la baja +3%/año)
  techo = participación máxima de un recién llegado × SAM (A 0,2% · B 0,3% · C 0,5%)
  capacidad = 5.000 t × rampa (40% el año de certificación, 70% el siguiente, 100% después; 0 antes)
  AgroPorc = mín(capacidad, techo)  → se registra qué limita: la capacidad o el mercado

Además, gold.fact_landed_cost: costo puesto en China de cada proveedor en cada escenario. El caso
comercial escala los aranceles adicionales (represalias) y Ecuador paga la tasa del acuerdo del año en
que empieza a exportar (o el NMF si nunca certifica).

Uso:  python -m src.scenarios
"""
from __future__ import annotations

import sys
from datetime import date

import pandas as pd
from sqlalchemy import text

from src import landed_cost as lc
from src.config import ROOT_DIR
from src.db import GOLD, SILVER, get_engine, insert_df

REPORT = ROOT_DIR / "docs" / "scenarios.md"
BASE_YEAR = 2025                       # último año completo en la base espejo y en USDA
SUPPLIERS = ("CHL", "ECU", "ESP", "DNK", "USA", "CAN", "BRA")
OFFAL = "020649"


# ---------------------------------------------------------------- reglas puras (probadas sin base de datos)
def ramp_share(year_n: int, cert_year: int | None, y1: float, y2: float) -> float:
    """Fracción de la capacidad disponible en el año `year_n`: 0 antes de certificar; luego y1, y2 y 100%."""
    if cert_year is None or year_n < cert_year:
        return 0.0
    k = year_n - cert_year
    return y1 / 100 if k == 0 else y2 / 100 if k == 1 else 1.0


def market_index(calendar_year: int, usda_ratio: dict[int, float], trend_pct: float) -> float:
    """Tamaño del mercado relativo a 2025: USDA para los años que proyecta y luego la tendencia del escenario."""
    if calendar_year in usda_ratio:
        return usda_ratio[calendar_year]
    last = max(usda_ratio)
    return usda_ratio[last] * (1 + trend_pct / 100) ** (calendar_year - last)


def volume(capacity_t: float, som_cap_t: float) -> tuple[float, str]:
    """Volumen vendible y qué lo limita."""
    if capacity_t <= 0:
        return 0.0, "none"
    return (capacity_t, "capacity") if capacity_t <= som_cap_t else (som_cap_t, "market")


def num(v) -> float:
    """Vacío (None o NaN) → 0. Ojo: `NaN or 0` devuelve NaN en Python, porque NaN cuenta como verdadero."""
    return 0.0 if v is None or pd.isna(v) else float(v)


def rate_at(schedule: pd.DataFrame, d: date) -> float | None:
    """Tasa vigente en la fecha `d` según un calendario SCD2 (valid_from, valid_to, rate_pct)."""
    hit = schedule[(schedule["valid_from"] <= d) & (schedule["valid_to"] >= d)]
    return float(hit["rate_pct"].iloc[0]) if len(hit) else None


# ---------------------------------------------------------------- lectura
def read_inputs(conn) -> dict:
    scen = pd.read_sql(text(f"SELECT scenario_key, code, trade_case, china_selfsuff, cert_year FROM {GOLD}.dim_scenario"), conn)
    scen["cert_year"] = scen["cert_year"].astype("Int64")
    # Valor de cada supuesto en cada escenario (última versión del supuesto)
    vals = pd.read_sql(text(f"""
        SELECT s.scenario_id AS scenario_key, a.name,
               CASE sa.which_value WHEN 'min' THEN a.value_min WHEN 'max' THEN a.value_max ELSE a.value_base END AS value
        FROM {SILVER}.scenario_assumption sa
        JOIN {SILVER}.scenario s   ON s.scenario_id = sa.scenario_id
        JOIN {SILVER}.assumption a ON a.assumption_id = sa.assumption_id"""), conn)
    params = vals.pivot_table(index="scenario_key", columns="name", values="value", aggfunc="first").astype(float)
    base = conn.execute(text(f"""
        SELECT SUM(f.tonnes), SUM(CASE WHEN p.is_sam THEN f.tonnes ELSE 0 END)
        FROM {GOLD}.fact_china_imports f
        JOIN {GOLD}.dim_product p ON p.product_key = f.product_key
        JOIN {GOLD}.mirror_coverage cov ON cov.date_key = f.date_key AND cov.is_complete
        WHERE f.basis = 'mirror' AND f.date_key BETWEEN :a AND :b"""),
        {"a": BASE_YEAR * 10000 + 101, "b": BASE_YEAR * 10000 + 1201}).one()
    usda = dict(conn.execute(text(f"""SELECT market_year, imports_kt FROM {GOLD}.fact_market_balance
                                      WHERE psd_code = 'CH' AND market_year >= {BASE_YEAR}""")).all())
    schedule = pd.read_sql(text(f"""
        SELECT m.valid_from, m.valid_to, m.rate_pct, m.measure_type
        FROM {SILVER}.trade_measure m
        JOIN {SILVER}.country t ON t.country_id = m.target_id AND t.iso3 = 'ECU'
        WHERE m.hs_code = '{OFFAL}' AND m.measure_type = 'preferential'"""), conn)
    for c in ("valid_from", "valid_to"):
        schedule[c] = pd.to_datetime(schedule[c].astype(str).replace("9999-12-31", "2262-04-11")).dt.date
    return dict(scenarios=scen, params=params, tam_base=float(base[0]), sam_base=float(base[1]),
                usda_ratio={int(y): float(v) / float(usda[BASE_YEAR]) for y, v in usda.items()},
                ec_schedule=schedule, assumptions=lc.read_assumptions(conn), market=read_market_detail(conn))


def read_market_detail(conn) -> pd.DataFrame:
    """Como landed_cost.read_market, con los componentes del arancel separados."""
    m = lc.read_market(conn)
    parts = pd.read_sql(text(f"""
        SELECT c.iso3, p.hs_code, t.additional_pct, t.antidumping_min_pct
        FROM {GOLD}.fact_tariff_applied t
        JOIN {GOLD}.dim_country c ON c.country_key = t.origin_key
        JOIN {GOLD}.dim_product p ON p.product_key = t.product_key
        WHERE t.date_key = (SELECT MAX(date_key) FROM {GOLD}.dim_date WHERE date <= CURDATE())"""), conn)
    return m.merge(parts, on=["iso3", "hs_code"], how="left")


# ---------------------------------------------------------------- modelo
def build_market(inp: dict) -> pd.DataFrame:
    rows = []
    for s in inp["scenarios"].itertuples():
        p = inp["params"].loc[s.scenario_key]
        cert = None if pd.isna(s.cert_year) else int(s.cert_year)
        start = int(p["project_start_year"])
        for n in range(1, 11):
            year = start + n
            idx = market_index(year, inp["usda_ratio"], p["china_imports_trend_pct"])
            sam = inp["sam_base"] * idx
            cap_t = p["agroporc_capacity_t"] * ramp_share(n, cert, p["entry_ramp_y1_pct"], p["entry_ramp_y2_pct"])
            som_cap = sam * p["som_max_share_pct"] / 100
            vol, binding = volume(cap_t, som_cap)
            pref = rate_at(inp["ec_schedule"], date(year, 7, 1))
            rows.append(dict(scenario_key=s.scenario_key, year_n=n, calendar_year=year,
                             tam_t=round(inp["tam_base"] * idx, 1), sam_t=round(sam, 1), som_cap_t=round(som_cap, 1),
                             capacity_t=round(cap_t, 1), agroporc_t=round(vol, 1), binding=binding,
                             ecuador_duty_pct=round(pref if (pref is not None and cert is not None) else 12.0, 2)))
    return pd.DataFrame(rows)


def build_landed(inp: dict, market_rows: pd.DataFrame, ckeys: dict, pkeys: dict) -> pd.DataFrame:
    a, m = inp["assumptions"], inp["market"]
    payload_kg = a.loc["reefer_payload_t", "base"] * 1000
    ins = a.loc["cargo_insurance_pct", "base"]
    chile_fob = m[m["iso3"] == "CHL"].set_index("hs_code")["fob_usd_kg"].astype(float).to_dict()
    rows = []
    for s in inp["scenarios"].itertuples():
        factor = inp["params"].loc[s.scenario_key, "retaliation_factor"]
        first = market_rows[(market_rows["scenario_key"] == s.scenario_key) & (market_rows["agroporc_t"] > 0)]
        ec_duty = float(first["ecuador_duty_pct"].iloc[0]) if len(first) else 12.0
        for r in m[m["iso3"].isin(SUPPLIERS)].itertuples():
            fob = chile_fob.get(r.hs_code) if r.iso3 == "ECU" else r.fob_usd_kg
            if fob is None or pd.isna(fob):
                continue
            if r.iso3 == "ECU":
                duty = ec_duty
            else:
                base_duty = r.preferential_pct if pd.notna(r.preferential_pct) else r.mfn_pct
                duty = num(base_duty) + num(r.additional_pct) * factor + num(r.antidumping_min_pct)
            fr = a.loc[f"freight_reefer40_{lc.route_of(r.iso3)}", "base"] / payload_kg
            x = lc.landed_cost(float(fob), fr, ins, duty)
            rows.append(dict(scenario_key=s.scenario_key, supplier_key=ckeys[r.iso3], product_key=pkeys[r.hs_code],
                             fob_usd_kg=round(x.fob, 4), freight_usd_kg=round(x.freight, 4),
                             insurance_usd_kg=round(x.insurance, 4), cif_usd_kg=round(x.cif, 4),
                             total_duty_pct=round(duty, 2), landed_usd_kg=round(x.landed, 4),
                             _access=bool(r.has_access)))
    out = pd.DataFrame(rows)
    best = out[out["_access"]].groupby(["scenario_key", "product_key"])["landed_usd_kg"].min()
    out["gap_vs_best_usd_kg"] = (out["landed_usd_kg"] - out.set_index(["scenario_key", "product_key"]).index.map(best)).round(4)
    return out.drop(columns="_access")


# ---------------------------------------------------------------- carga y reporte
def main() -> int:
    pd.set_option("display.width", 180)
    print("=== Pork to China · Fase 10.2 · mercado y costo por escenario ===\n")
    with get_engine("etl").begin() as conn:
        inp = read_inputs(conn)
        # Claves de países y de productos en diccionarios separados: son enteros que se repiten entre tablas
        ckeys = dict(conn.execute(text(f"SELECT iso3, country_key FROM {GOLD}.dim_country")).all())
        pkeys = dict(conn.execute(text(f"SELECT hs_code, product_key FROM {GOLD}.dim_product")).all())
        cnames = dict(conn.execute(text(f"SELECT country_key, name_es FROM {GOLD}.dim_country")).all())
        market = build_market(inp)
        landed = build_landed(inp, market, ckeys, pkeys)
        for t in ("fact_scenario_market", "fact_landed_cost"):
            conn.execute(text(f"DELETE FROM {GOLD}.{t}"))
        insert_df(conn, market, GOLD, "fact_scenario_market")
        insert_df(conn, landed, GOLD, "fact_landed_cost")

    codes = inp["scenarios"].set_index("scenario_key")["code"]
    print(f"Base {BASE_YEAR} (espejo): TAM {inp['tam_base']:,.0f} t · SAM {inp['sam_base']:,.0f} t".replace(",", "."))
    print("Índice USDA de importaciones vs 2025: " +
          " · ".join(f"{y}: {v:.3f}".replace(".", ",") for y, v in sorted(inp["usda_ratio"].items())))
    summ = (market.assign(code=market["scenario_key"].map(codes))
            .groupby("code").agg(sam_2027=("sam_t", "first"), sam_2036=("sam_t", "last"),
                                 techo_2036=("som_cap_t", "last"), t_10_anios=("agroporc_t", "sum"),
                                 primer_anio=("agroporc_t", lambda v: next((i + 1 for i, x in enumerate(v) if x > 0), None)),
                                 limita_mercado=("binding", lambda v: int((v == "market").sum()))))
    summ = summ.reindex(sorted(summ.index, key=lambda c: (c[0], c.split("-")[1], c.split("-")[2])))
    print("\n[1/2] Volumen de AgroPorc por escenario (t; techo = participación máxima × SAM)")
    print(summ.round(0).to_string())

    sel = landed.merge(pd.DataFrame({"scenario_key": codes.index, "code": codes.values}), on="scenario_key")
    sel = sel[sel["code"].isin(["A-up-2", "B-up-2", "C-up-2"]) & (sel["product_key"] == pkeys[OFFAL])]
    piv = sel.assign(proveedor=sel["supplier_key"].map(cnames)).pivot_table(
        index="proveedor", columns="code", values="landed_usd_kg").round(2).sort_values("B-up-2")
    print("\n[2/2] Costo puesto en China de vísceras (020649, USD/kg) según el caso comercial (cert. año 2)")
    print(piv.to_string())

    REPORT.write_text("\n".join([
        "# Mercado y costo por escenario (TAM–SAM–SOM)", "",
        "Generado por `src/scenarios.py`. Toneladas de peso neto (base espejo). Año 1 = 2027. "
        "AgroPorc = mín(5.000 t × rampa 40-70-100 desde la certificación, techo de participación × SAM).", "",
        "## Volumen por escenario", "", summ.round(0).reset_index().to_markdown(index=False) if hasattr(summ, "to_markdown") and False else
        "\n".join(["| escenario | " + " | ".join(summ.columns) + " |", "|---|" + "---|" * len(summ.columns)] +
                  [f"| {i} | " + " | ".join("—" if pd.isna(v) else f"{v:,.0f}".replace(",", ".") for v in r) + " |"
                   for i, r in summ.round(0).iterrows()]),
        "", "## Costo puesto en China de vísceras 020649 (USD/kg), certificación en el año 2", "",
        "\n".join(["| proveedor | " + " | ".join(piv.columns) + " |", "|---|" + "---|" * len(piv.columns)] +
                  [f"| {i} | " + " | ".join(f"{v:.2f}".replace(".", ",") for v in r) + " |" for i, r in piv.iterrows()]),
        ""]), encoding="utf-8")
    print(f"\nReporte: {REPORT.relative_to(ROOT_DIR)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
