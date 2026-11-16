"""
finance.py · Fase 10.3 · Flujo de caja, VAN, TIR y punto de equilibrio de AgroPorc por escenario

USD reales, años 0–10 (0 = 2026, inversión). Para cada año n ≥ 1:
    ingresos       = toneladas del escenario × FOB (tomador de precio: el de Chile en vísceras)
    costo variable = toneladas × (valor local de la víscera + proceso + congelación + logística)
    costo fijo     = desde el primer año en que exporta
    EBITDA         = ingresos − costo variable − costo fijo
    impuesto       = máx(EBITDA − depreciación, 0) × 36,25%   (sin arrastre de pérdidas: conservador)
    capital de trabajo = meses de costo variable; se invierte cuando crece y se recupera en el año 10
    flujo neto     = EBITDA − impuesto − Δ capital de trabajo   (año 0: − inversión)

Resultados por escenario: VAN al 12%, TIR, payback simple y descontado, divisas, empleos y dos puntos
de equilibrio: el VALOR LOCAL MÁXIMO DE LA VÍSCERA (el dato que no se pudo verificar) y las toneladas
anuales necesarias si el mercado no limitara.

Uso:  python -m src.finance
"""
from __future__ import annotations

import sys

import numpy as np
import numpy_financial as npf
import pandas as pd
from sqlalchemy import text

from src.config import ROOT_DIR
from src.db import GOLD, SILVER, get_engine, insert_df
from src.scenarios import ramp_share

REPORT = ROOT_DIR / "docs" / "finance.md"
CAPEX_ITEMS = ("capex_blast_freezer", "capex_cold_storage", "capex_plant_upgrade", "capex_china_registration")
VAR_ITEMS = ("offal_local_value_usd_kg", "processing_cost_usd_kg", "freezing_cost_usd_kg", "export_logistics_usd_kg")


# ---------------------------------------------------------------- reglas puras (probadas sin base de datos)
def cashflow(tonnes: list[float], p: dict) -> pd.DataFrame:
    """Flujo de caja anual (años 0–10) para una trayectoria de toneladas de los años 1–10."""
    capex = sum(p[k] for k in CAPEX_ITEMS)
    var_kg = sum(p[k] for k in VAR_ITEMS)
    rate = p["discount_rate"] / 100
    years = range(0, len(tonnes) + 1)
    t = np.array([0.0, *tonnes])
    started = np.cumsum(t > 0) > 0                                 # desde el primer año que exporta
    revenue = t * 1000 * p["ecuador_fob_usd_kg_offal"]
    var_cost = t * 1000 * var_kg
    fixed = np.where(started, p["fixed_cost_usd_year"], 0.0)
    ebitda = revenue - var_cost - fixed
    dep = np.array([0.0] + [capex / p["depreciation_years"]] * len(tonnes))
    tax = np.maximum(ebitda - dep, 0) * p["effective_tax_pct"] / 100
    wc = var_cost * p["working_capital_months"] / 12
    wc_change = np.diff(np.concatenate([[0.0], wc]))
    wc_change[-1] -= wc[-1]                                        # se recupera al final del horizonte
    capex_v = np.array([capex] + [0.0] * len(tonnes))
    net = ebitda - tax - wc_change - capex_v
    dcf = net / (1 + rate) ** np.array(list(years))
    return pd.DataFrame({"year_n": list(years), "tonnes": t, "capex": capex_v, "revenue": revenue,
                         "opex": var_cost + fixed, "tax": tax, "net_cashflow": net, "discounted_cf": dcf,
                         "cumulative_dcf": np.cumsum(dcf)})


def payback(flows: np.ndarray) -> float | None:
    """Años hasta recuperar la inversión (interpolando dentro del año). None si no se recupera."""
    cum = np.cumsum(flows)
    for i in range(1, len(cum)):
        if cum[i] >= 0 > cum[i - 1]:
            return round(i - 1 + (-cum[i - 1]) / (cum[i] - cum[i - 1]), 2)
    return None


def irr(flows: np.ndarray) -> float | None:
    if not (flows < 0).any() or not (flows > 0).any():
        return None
    r = npf.irr(flows)
    return None if r is None or np.isnan(r) else round(r * 100, 2)


def bisect(f, lo: float, hi: float, tol: float = 1e-4) -> float | None:
    """Raíz de una función monótona en [lo, hi]; None si no cambia de signo."""
    flo, fhi = f(lo), f(hi)
    if flo == 0:
        return lo
    if np.sign(flo) == np.sign(fhi):
        return None
    for _ in range(100):
        mid = (lo + hi) / 2
        fm = f(mid)
        if abs(hi - lo) < tol:
            break
        lo, hi, flo = (mid, hi, fm) if np.sign(fm) == np.sign(flo) else (lo, mid, flo)
    return (lo + hi) / 2


def evaluate(tonnes: list[float], p: dict, cert_year: int | None) -> dict:
    cf = cashflow(tonnes, p)
    npv = float(cf["discounted_cf"].sum())
    sells = any(x > 0 for x in tonnes)
    # Valor local máximo de la víscera con el que VAN = 0 (el VAN baja cuando la víscera vale más)
    be_offal = bisect(lambda v: cashflow(tonnes, p | {"offal_local_value_usd_kg": v})["discounted_cf"].sum(),
                      -5.0, p["ecuador_fob_usd_kg_offal"], tol=1e-7) if sells else None
    # Toneladas anuales (con la misma rampa) que darían VAN = 0 si el mercado no limitara
    be_t = None
    if cert_year is not None:
        path = lambda c: [c * ramp_share(n, cert_year, p["entry_ramp_y1_pct"], p["entry_ramp_y2_pct"]) for n in range(1, 11)]
        be_t = bisect(lambda c: cashflow(path(c), p)["discounted_cf"].sum(), 0.0, 1e6, tol=1)
    peak = max(tonnes) if tonnes else 0
    return dict(npv_usd=round(npv, 2), irr_pct=irr(cf["net_cashflow"].to_numpy()),
                payback_years=payback(cf["net_cashflow"].to_numpy()),
                discounted_payback_years=payback(cf["discounted_cf"].to_numpy()),
                breakeven_tonnes=None if be_t is None else round(be_t, 2),
                breakeven_offal_usd_kg=None if be_offal is None else round(be_offal, 3),
                fx_usd=round(float(cf["revenue"].sum()), 2),
                jobs=int(round(p["jobs_fixed"] + p["jobs_per_1000t"] * peak / 1000)) if sells else 0), cf


# ---------------------------------------------------------------- lectura, carga y reporte
def read_inputs(conn):
    scen = pd.read_sql(text(f"SELECT scenario_key, code, cert_year FROM {GOLD}.dim_scenario"), conn)
    vals = pd.read_sql(text(f"""
        SELECT sa.scenario_id AS scenario_key, a.name,
               CASE sa.which_value WHEN 'min' THEN a.value_min WHEN 'max' THEN a.value_max ELSE a.value_base END AS value
        FROM {SILVER}.scenario_assumption sa JOIN {SILVER}.assumption a ON a.assumption_id = sa.assumption_id"""), conn)
    params = vals.pivot_table(index="scenario_key", columns="name", values="value", aggfunc="first").astype(float)
    market = pd.read_sql(text(f"SELECT scenario_key, year_n, agroporc_t FROM {GOLD}.fact_scenario_market ORDER BY year_n"), conn)
    return scen, params, market


def main() -> int:
    pd.set_option("display.width", 200)
    print("=== Pork to China · Fase 10.3 · flujo de caja, VAN y TIR de AgroPorc ===\n")
    results, flows = [], []
    with get_engine("etl").begin() as conn:
        scen, params, market = read_inputs(conn)
        for s in scen.itertuples():
            p = params.loc[s.scenario_key].to_dict()
            tonnes = market.loc[market["scenario_key"] == s.scenario_key, "agroporc_t"].astype(float).tolist()
            cert = None if pd.isna(s.cert_year) else int(s.cert_year)
            res, cf = evaluate(tonnes, p, cert)
            results.append(dict(scenario_key=s.scenario_key, **res))
            flows.append(cf.assign(scenario_key=s.scenario_key))
        cash = pd.concat(flows)[["scenario_key", "year_n", "tonnes", "capex", "revenue", "opex",
                                 "net_cashflow", "discounted_cf", "cumulative_dcf"]].round(2)
        res = pd.DataFrame(results)
        for t in ("fact_scenario_cashflow", "fact_scenario_result"):
            conn.execute(text(f"DELETE FROM {GOLD}.{t}"))
        insert_df(conn, cash, GOLD, "fact_scenario_cashflow")
        insert_df(conn, res, GOLD, "fact_scenario_result")

    p0 = params.iloc[0]
    capex = sum(p0[k] for k in CAPEX_ITEMS)
    margin = p0["ecuador_fob_usd_kg_offal"] - sum(p0[k] for k in VAR_ITEMS)
    print(f"Inversión: {capex:,.0f} USD · FOB {p0['ecuador_fob_usd_kg_offal']:.2f} − costo variable "
          f"{sum(p0[k] for k in VAR_ITEMS):.2f} = margen {margin:.2f} USD/kg · tasa {p0['discount_rate']:.0f}%".replace(",", "."))
    show = res.merge(scen[["scenario_key", "code"]]).set_index("code").sort_values("npv_usd", ascending=False)
    view = pd.DataFrame({
        "VAN_kUSD": (show["npv_usd"] / 1000).round(0),
        "TIR_%": show["irr_pct"],
        "payback": show["payback_years"],
        "víscera_máx": show["breakeven_offal_usd_kg"],
        "t_equilibrio": pd.to_numeric(show["breakeven_tonnes"], errors="coerce").round(0),
        "divisas_MUSD": (show["fx_usd"] / 1e6).round(1),
        "empleos": show["jobs"]})
    print("\nResultados por escenario (VAN al 12%; víscera_máx = valor local de la víscera con el que VAN = 0)")
    print(view.to_string())
    pos = (show["npv_usd"] > 0).sum()
    print(f"\nEscenarios con VAN positivo: {pos} de {len(show)}")

    fmt = lambda v: "—" if pd.isna(v) else (f"{v:,.0f}" if abs(v) >= 100 else f"{v:,.2f}").replace(",", "_").replace(".", ",").replace("_", ".")
    REPORT.write_text("\n".join([
        "# Flujo de caja, VAN y TIR de AgroPorc por escenario", "",
        "Generado por `src/finance.py`. USD reales; año 0 = 2026; tasa de descuento 12%; impuesto efectivo 36,25%. "
        "Supuestos en `silver.assumption` (ver `docs/assumptions.md`).", "",
        f"Inversión base: {fmt(capex)} USD · margen variable: {margin:.2f} USD/kg".replace(".", ","), "",
        "**víscera_máx**: valor local máximo de la víscera con el que el proyecto todavía tiene VAN = 0. "
        "Si en Ecuador la víscera vale menos que eso, exportar conviene.  ",
        "**t_equilibrio**: toneladas anuales (con la rampa 40-70-100) necesarias para VAN = 0 si el mercado no limitara.", "",
        "| escenario | " + " | ".join(view.columns) + " |", "|---|" + "---|" * len(view.columns)] +
        [f"| {i} | " + " | ".join(fmt(v) for v in r) + " |" for i, r in view.iterrows()] +
        ["", f"Escenarios con VAN positivo: {pos} de {len(show)}.", ""]), encoding="utf-8")
    print(f"\nReporte: {REPORT.relative_to(ROOT_DIR)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
