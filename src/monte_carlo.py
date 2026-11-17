"""
Pork to China · Fase 14.3 · Monte Carlo del VAN de AgroPorc

Para cada uno de los 24 escenarios (que fijan el caso comercial, la autosuficiencia china y el año de
certificación, y con ellos el techo de mercado de cada año), sortea N combinaciones de los supuestos de
costo, precio y capacidad con distribución TRIANGULAR (mínimo, base, máximo de silver.assumption).
La tasa de descuento NO se sortea: es una decisión del inversionista (12%), no una incertidumbre.
Los supuestos se sortean de forma independiente (limitación documentada: en la realidad algunos se mueven juntos).

El flujo de caja se calcula vectorizado con NumPy y reproduce exactamente src/finance.cashflow (lo verifica
una prueba): N × 24 evaluaciones en segundos, sin IRR ni bisección por sorteo.

Resultados en gold:
  fact_mc_summary   P(VAN > 0), media y percentiles 5/50/95 por escenario
  fact_mc_hist      histograma del VAN por escenario (40 intervalos)
  fact_mc_tornado   sensibilidad por supuesto: VAN con el supuesto en su mín y en su máx (los demás en base)
                    y correlación de Spearman entre el supuesto sorteado y el VAN
Uso:  python -m src.monte_carlo [--n 10000]
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd
from scipy import stats
from sqlalchemy import text

from src import finance as fi
from src.config import ROOT_DIR
from src.db import GOLD, SILVER, get_engine, insert_df
from src.scenarios import ramp_share

SEED = 2026
N_DEFAULT = 10_000
REPORT = ROOT_DIR / "docs" / "monte_carlo.md"
# Supuestos inciertos que se sortean (todos con mín < máx). Los de mercado definen el escenario y no se sortean.
UNCERTAIN = ("offal_local_value_usd_kg", "ecuador_fob_usd_kg_offal", "agroporc_capacity_t",
             "processing_cost_usd_kg", "freezing_cost_usd_kg", "export_logistics_usd_kg", "fixed_cost_usd_year",
             "working_capital_months", *fi.CAPEX_ITEMS)
LABELS = {"offal_local_value_usd_kg": "Valor local de la víscera", "ecuador_fob_usd_kg_offal": "Precio FOB de exportación",
          "agroporc_capacity_t": "Capacidad de la planta", "processing_cost_usd_kg": "Costo de proceso",
          "freezing_cost_usd_kg": "Costo de congelación", "export_logistics_usd_kg": "Logística de exportación",
          "fixed_cost_usd_year": "Costo fijo anual", "working_capital_months": "Capital de trabajo (meses)",
          "capex_blast_freezer": "Inversión: túnel de congelación", "capex_cold_storage": "Inversión: cámara de frío",
          "capex_plant_upgrade": "Inversión: adecuación de planta",
          "capex_china_registration": "Inversión: habilitación para China"}


# ---------------------------------------------------------------- motor vectorizado
def npv_vectorized(p: dict[str, np.ndarray], ramps: np.ndarray, caps: np.ndarray) -> np.ndarray:
    """
    VAN para N juegos de supuestos a la vez. p: cada supuesto es un array (N,) o un escalar.
    ramps, caps: (Y,) fracción de capacidad y techo de mercado de los años 1..Y. Misma lógica que finance.cashflow.
    """
    n = np.broadcast(*[np.asarray(v) for v in p.values()]).shape or (1,)
    g = {k: np.broadcast_to(np.asarray(v, dtype=float), n)[:, None] for k, v in p.items()}
    Y = len(caps)
    tonnes = np.minimum(g["agroporc_capacity_t"] * ramps[None, :], caps[None, :])
    tonnes = np.where(g["agroporc_capacity_t"] * ramps[None, :] > 0, tonnes, 0.0)
    t = np.concatenate([np.zeros((n[0], 1)), tonnes], axis=1)                 # año 0 sin toneladas
    capex = sum(g[k] for k in fi.CAPEX_ITEMS)
    var_kg = sum(g[k] for k in fi.VAR_ITEMS)
    started = np.cumsum(t > 0, axis=1) > 0
    revenue = t * 1000 * g["ecuador_fob_usd_kg_offal"]
    var_cost = t * 1000 * var_kg
    fixed = np.where(started, g["fixed_cost_usd_year"], 0.0)
    ebitda = revenue - var_cost - fixed
    dep = np.concatenate([np.zeros((n[0], 1)), np.repeat(capex / g["depreciation_years"], Y, axis=1)], axis=1)
    tax = np.maximum(ebitda - dep, 0) * g["effective_tax_pct"] / 100
    wc = var_cost * g["working_capital_months"] / 12
    wc_change = np.diff(np.concatenate([np.zeros((n[0], 1)), wc], axis=1), axis=1)
    wc_change[:, -1] -= wc[:, -1]
    capex_v = np.concatenate([capex, np.zeros((n[0], Y))], axis=1)
    net = ebitda - tax - wc_change - capex_v
    disc = (1 + g["discount_rate"] / 100) ** np.arange(Y + 1)[None, :]
    return (net / disc).sum(axis=1)


def triangular(rng: np.random.Generator, lo: float, mode: float, hi: float, n: int) -> np.ndarray:
    if hi <= lo:
        return np.full(n, mode)
    return rng.triangular(lo, mode, hi, n)


# ---------------------------------------------------------------- datos
def load(conn) -> tuple[pd.DataFrame, pd.DataFrame, dict[int, np.ndarray], pd.DataFrame]:
    sc = pd.read_sql(text(f"SELECT scenario_key, code, cert_year FROM {GOLD}.dim_scenario ORDER BY scenario_key"), conn)
    params = pd.read_sql(text(f"SELECT scenario_key, name, value FROM {GOLD}.v_scenario_params"), conn)
    params["value"] = params["value"].astype(float)
    ranges = pd.read_sql(text(f"""
        SELECT a.name, a.value_min, a.value_base, a.value_max FROM {SILVER}.assumption a
        WHERE a.version = (SELECT MAX(b.version) FROM {SILVER}.assumption b WHERE b.name = a.name)"""), conn)
    ranges = ranges.set_index("name").astype(float)
    caps = {k: g.sort_values("year_n")["som_cap_t"].astype(float).to_numpy() for k, g in pd.read_sql(text(
        f"SELECT scenario_key, year_n, som_cap_t FROM {GOLD}.fact_scenario_market"), conn).groupby("scenario_key")}
    return sc, params, caps, ranges


# ---------------------------------------------------------------- simulación
def simulate(n: int = N_DEFAULT, seed: int = SEED):
    with get_engine("etl").connect() as conn:
        sc, params, caps, ranges = load(conn)
    rng = np.random.default_rng(seed)
    # Un solo juego de sorteos para todos los escenarios (números aleatorios comunes): las diferencias entre
    # escenarios se deben al escenario, no al azar.
    draws = {k: triangular(rng, *ranges.loc[k, ["value_min", "value_base", "value_max"]], n) for k in UNCERTAIN}
    summary, hist, tornado = [], [], []
    for s in sc.itertuples():
        base = params[params["scenario_key"] == s.scenario_key].set_index("name")["value"].to_dict()
        cert = None if pd.isna(s.cert_year) else int(s.cert_year)
        Y = len(caps[s.scenario_key])
        ramps = np.array([ramp_share(y, cert, base["entry_ramp_y1_pct"], base["entry_ramp_y2_pct"])
                          for y in range(1, Y + 1)])
        p = {k: v for k, v in base.items()} | draws
        npv = npv_vectorized(p, ramps, caps[s.scenario_key])
        q5, q50, q95 = np.percentile(npv, [5, 50, 95])
        summary.append({"scenario_key": s.scenario_key, "n_draws": n, "p_npv_pos": float((npv > 0).mean()),
                        "npv_mean": float(npv.mean()), "npv_p05": float(q5), "npv_p50": float(q50),
                        "npv_p95": float(q95), "npv_base": float(npv_vectorized(base, ramps, caps[s.scenario_key])[0])})
        counts, edges = np.histogram(npv, bins=40)
        hist += [{"scenario_key": s.scenario_key, "bin": i, "bin_from": float(edges[i]), "bin_to": float(edges[i + 1]),
                  "n": int(c)} for i, c in enumerate(counts)]
        for k in UNCERTAIN:
            lo, hi = (npv_vectorized(base | {k: ranges.loc[k, c]}, ramps, caps[s.scenario_key])[0]
                      for c in ("value_min", "value_max"))
            rho = stats.spearmanr(draws[k], npv).statistic if np.ptp(npv) > 0 else 0.0
            tornado.append({"scenario_key": s.scenario_key, "assumption": k, "label_es": LABELS[k],
                            "npv_at_min": float(lo), "npv_at_max": float(hi), "swing": float(abs(hi - lo)),
                            "spearman": float(0.0 if np.isnan(rho) else rho)})
    return sc, pd.DataFrame(summary), pd.DataFrame(hist), pd.DataFrame(tornado)


def save(summary: pd.DataFrame, hist: pd.DataFrame, tornado: pd.DataFrame) -> None:
    with get_engine("etl").begin() as conn:
        for t in ("fact_mc_summary", "fact_mc_hist", "fact_mc_tornado"):
            conn.execute(text(f"DELETE FROM {GOLD}.{t}"))
        insert_df(conn, summary, GOLD, "fact_mc_summary")
        insert_df(conn, hist, GOLD, "fact_mc_hist")
        insert_df(conn, tornado, GOLD, "fact_mc_tornado")


def report(sc: pd.DataFrame, summary: pd.DataFrame, tornado: pd.DataFrame, n: int) -> str:
    m = summary.merge(sc, on="scenario_key")
    cert = m[m["cert_year"].notna()]
    lines = ["# Monte Carlo del VAN de AgroPorc", "",
             f"Generado por `src/monte_carlo.py`: {n:,} sorteos triangulares (mín–base–máx) de {len(UNCERTAIN)} supuestos ".replace(",", ".")
             + f"de costo, precio y capacidad; semilla {SEED}; los mismos sorteos en los 24 escenarios. Tasa de descuento "
             "fija en 12%. Supuestos independientes entre sí.", "",
             f"**Probabilidad de VAN positivo en los escenarios con certificación:** de {cert.p_npv_pos.min():.0%} a "
             f"{cert.p_npv_pos.max():.0%} (mediana {cert.p_npv_pos.median():.0%}). Sin certificación: 0%.", "",
             "| escenario | P(VAN > 0) | VAN p5 (M USD) | VAN mediana | VAN p95 | VAN con valores base |",
             "|---|---|---|---|---|---|"]
    for r in m.sort_values("p_npv_pos", ascending=False).itertuples():
        lines.append(f"| {r.code} | {r.p_npv_pos:.1%} | {r.npv_p05 / 1e6:+.2f} | {r.npv_p50 / 1e6:+.2f} | "
                     f"{r.npv_p95 / 1e6:+.2f} | {r.npv_base / 1e6:+.2f} |")
    central = m.loc[m["code"] == "B-up-4", "scenario_key"].iloc[0] if (m["code"] == "B-up-4").any() else cert.scenario_key.iloc[0]
    tc = tornado[tornado["scenario_key"] == central].sort_values("swing", ascending=False)
    lines += ["", f"## Qué supuesto pesa más (escenario {m.set_index('scenario_key').loc[central, 'code']})", "",
              "| supuesto | VAN con el mínimo (M USD) | VAN con el máximo | rango | Spearman |", "|---|---|---|---|---|"]
    for r in tc.itertuples():
        lines.append(f"| {r.label_es} | {r.npv_at_min / 1e6:+.2f} | {r.npv_at_max / 1e6:+.2f} | "
                     f"{r.swing / 1e6:.2f} | {r.spearman:+.2f} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=N_DEFAULT)
    a = ap.parse_args(argv)
    print(f"=== Pork to China · Fase 14.3 · Monte Carlo ({a.n:,} sorteos) ===\n".replace(",", "."))
    sc, summary, hist, tornado = simulate(a.n)
    save(summary, hist, tornado)
    txt = report(sc, summary, tornado, a.n)
    REPORT.write_text(txt, encoding="utf-8")
    print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
