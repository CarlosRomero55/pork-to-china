"""
Pork to China · Fase 14.2 · Serie de tiempo interrumpida (ITS)

Pregunta: ¿la guerra comercial cambió la participación de EE. UU. en las importaciones chinas de vísceras
de cerdo, más allá de la tendencia y la estacionalidad que ya traía?

Diseño (regresión segmentada, datos espejo mensuales desde 2015, que viven en silver y no entran a gold):
  y_t = b0 + b1·t + estacionalidad (11 dummies de mes)
        + b2·D18_t + b3·(t − t18)·D18_t        corte 1: represalias de abr-2018 (232 y luego 301)
        + b4·D20_t + b5·(t − t20)·D20_t        corte 2: acuerdo Fase Uno (feb-2020) + exclusiones de la 301
Medida principal: participación de EE. UU. en el VALOR (USD). Se usa valor porque EE. UU. no reportó el peso de
las vísceras en 2015 y en 2016-2017 lo estimó; la participación además neutraliza la peste porcina africana
(ago-2018), que subió la demanda china para todos los proveedores a la vez.
Robustez: (a) participación en toneladas (desde 2016); (b) log del valor de EE. UU. controlando por el log del
valor del resto de proveedores (otra forma de quitar el efecto de la PPA).
Ene-feb 2020: EE. UU. figura con ~0 (hueco de reporte, supuesto #48) → se tratan como faltantes.
Errores estándar de Newey-West (robustos a autocorrelación y heterocedasticidad), sin dependencias nuevas.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats
from sqlalchemy import text

from src.db import GOLD, SILVER, get_engine, insert_df
from src.logging_setup import get_logger

log = get_logger(__name__)

CUT_2018 = pd.Timestamp("2018-04-01")      # arancel 232: 2-abr-2018 (la 301 llega el 6-jul)
CUT_2020 = pd.Timestamp("2020-02-01")      # Fase Uno en vigor: 14-feb-2020; exclusiones desde mar-2020
GAP = [pd.Timestamp("2020-01-01"), pd.Timestamp("2020-02-01")]   # hueco de reporte de EE. UU. (supuesto #48)
START = pd.Timestamp("2015-01-01")


# ---------------------------------------------------------------- datos
def load_monthly(conn) -> pd.DataFrame:
    """Vísceras (espejo) por mes: valor y toneladas de EE. UU. y del resto, solo meses con cobertura completa."""
    df = pd.read_sql(text(f"""
        SELECT f.period AS date, (r.iso3 = 'USA') AS is_us,
               SUM(f.value_usd) AS value_usd, SUM(f.net_weight_kg) / 1000 AS tonnes
        FROM {SILVER}.trade_flow f
        JOIN {SILVER}.source s ON s.source_id = f.source_id AND s.name = 'comtrade_mirror'
        JOIN {SILVER}.country r ON r.country_id = f.reporter_id
        JOIN {SILVER}.country p ON p.country_id = f.partner_id AND p.iso3 = 'CHN'
        JOIN {SILVER}.hs_product h ON h.hs_code = f.hs_code AND h.product_group = 'offal'
        WHERE f.flow_type = 'X' AND f.period >= :start
        GROUP BY f.period, is_us"""), conn, params={"start": START.date()})
    df["date"] = pd.to_datetime(df["date"])
    for c in ("value_usd", "tonnes"):
        df[c] = pd.to_numeric(df[c])
    w = df.pivot_table(index="date", columns="is_us", values=["value_usd", "tonnes"], aggfunc="sum").fillna(0)
    out = pd.DataFrame({"us_value": w[("value_usd", 1)], "rest_value": w[("value_usd", 0)],
                        "us_t": w[("tonnes", 1)], "rest_t": w[("tonnes", 0)]})
    # Meses incompletos al final de la serie: se usa la cobertura que ya calcula gold (desde 2018)
    last_ok = conn.execute(text(f"""SELECT MAX(d.date) FROM {GOLD}.mirror_coverage m
                                    JOIN {GOLD}.dim_date d ON d.date_key = m.date_key
                                    WHERE m.is_complete = 1""")).scalar()
    out = out[out.index <= pd.Timestamp(last_ok)]
    return out


def outcomes(m: pd.DataFrame) -> dict[str, pd.Series]:
    """Las tres medidas, con el hueco de ene-feb 2020 como faltante."""
    share_v = 100 * m.us_value / (m.us_value + m.rest_value)
    share_t = (100 * m.us_t / (m.us_t + m.rest_t)).where(m.index >= pd.Timestamp("2016-01-01"))
    log_v = np.log(m.us_value.where(m.us_value > 0))
    ys = {"share_value": share_v, "share_tonnes": share_t, "log_us_value": log_v}
    return {k: v.where(~v.index.isin(GAP)) for k, v in ys.items()}


# ---------------------------------------------------------------- modelo
def design(idx: pd.DatetimeIndex, control: pd.Series | None = None) -> pd.DataFrame:
    t = (idx.year - START.year) * 12 + (idx.month - START.month)
    t18 = (CUT_2018.year - START.year) * 12 + CUT_2018.month - START.month
    t20 = (CUT_2020.year - START.year) * 12 + CUT_2020.month - START.month
    X = pd.DataFrame(index=idx)
    X["const"] = 1.0
    X["trend"] = t
    for mth in range(2, 13):
        X[f"m{mth:02d}"] = (idx.month == mth).astype(float)
    X["level_2018"] = (t >= t18).astype(float)
    X["slope_2018"] = np.where(t >= t18, t - t18, 0.0)
    X["level_2020"] = (t >= t20).astype(float)
    X["slope_2020"] = np.where(t >= t20, t - t20, 0.0)
    if control is not None:
        X["log_rest_value"] = control.reindex(idx).values
    return X


@dataclass
class Fit:
    name: str
    coef: pd.DataFrame          # term, estimate, se, t, p, ci_low, ci_high
    fitted: pd.Series
    counterfactual: pd.Series   # sin cortes (b2..b5 = 0)
    n: int
    r2: float
    lags: int
    cov: pd.DataFrame           # covarianza Newey-West de los coeficientes


def newey_west_ols(y: pd.Series, X: pd.DataFrame, lags: int | None = None) -> tuple[np.ndarray, np.ndarray, int]:
    """OLS con matriz de covarianza de Newey-West (núcleo de Bartlett)."""
    Xv, yv = X.to_numpy(float), y.to_numpy(float)
    n, k = Xv.shape
    lags = lags if lags is not None else int(np.floor(4 * (n / 100) ** (2 / 9)))
    xtx_inv = np.linalg.inv(Xv.T @ Xv)
    beta = xtx_inv @ Xv.T @ yv
    u = yv - Xv @ beta
    xu = Xv * u[:, None]
    s = xu.T @ xu
    for L in range(1, lags + 1):
        w = 1 - L / (lags + 1)
        g = xu[L:].T @ xu[:-L]
        s += w * (g + g.T)
    cov = xtx_inv @ s @ xtx_inv * n / (n - k)
    return beta, cov, lags


def fit(name: str, y: pd.Series, control: pd.Series | None = None) -> Fit:
    X = design(y.index, control)
    ok = y.notna() & X.notna().all(axis=1)
    beta, cov, lags = newey_west_ols(y[ok], X[ok])
    se = np.sqrt(np.diag(cov))
    dof = int(ok.sum()) - X.shape[1]
    tval = beta / se
    p = 2 * stats.t.sf(np.abs(tval), dof)
    q = stats.t.ppf(0.975, dof)
    coef = pd.DataFrame({"term": X.columns, "estimate": beta, "se": se, "t": tval, "p": p,
                         "ci_low": beta - q * se, "ci_high": beta + q * se})
    b = pd.Series(beta, index=X.columns)
    fitted = X.fillna(0) @ b
    cf_b = b.copy()
    cf_b[["level_2018", "slope_2018", "level_2020", "slope_2020"]] = 0
    counterfactual = X.fillna(0) @ cf_b
    resid = y[ok] - fitted[ok]
    r2 = float(1 - (resid ** 2).sum() / ((y[ok] - y[ok].mean()) ** 2).sum())
    return Fit(name, coef, fitted.where(X.notna().all(axis=1)), counterfactual.where(X.notna().all(axis=1)),
               int(ok.sum()), r2, lags, pd.DataFrame(cov, index=X.columns, columns=X.columns))


def effect_after(f: Fit, cut: str, months: int) -> tuple[float, float, float]:
    """Efecto total a `months` meses del corte: nivel + pendiente·meses, con su IC 95% (vía Newey-West)."""
    c = f.coef.set_index("term")
    a, b = f"level_{cut}", f"slope_{cut}"
    est = c.loc[a, "estimate"] + months * c.loc[b, "estimate"]
    # Var(a + m·b) = var(a) + m²·var(b) + 2m·cov(a, b), con la covarianza de Newey-West
    se = np.sqrt(f.cov.loc[a, a] + months ** 2 * f.cov.loc[b, b] + 2 * months * f.cov.loc[a, b])
    return float(est), float(est - 1.96 * se), float(est + 1.96 * se)


# ---------------------------------------------------------------- orquestación
def run() -> dict[str, Fit]:
    with get_engine("etl").connect() as conn:
        m = load_monthly(conn)
    ys = outcomes(m)
    fits = {
        "share_value": fit("share_value", ys["share_value"]),
        "share_tonnes": fit("share_tonnes", ys["share_tonnes"]),
        "log_us_value": fit("log_us_value", ys["log_us_value"], control=np.log(m.rest_value)),
    }
    series = []
    for k, f in fits.items():
        series.append(pd.DataFrame({"model": k, "date": ys[k].index, "observed": ys[k].values,
                                    "fitted": f.fitted.values, "counterfactual": f.counterfactual.values,
                                    "is_gap": ys[k].index.isin(GAP)}))
    series = pd.concat(series, ignore_index=True)
    coefs = pd.concat([f.coef.assign(model=k, n_obs=f.n, r2=f.r2, nw_lags=f.lags) for k, f in fits.items()],
                      ignore_index=True)
    with get_engine("etl").begin() as conn:
        conn.execute(text(f"DELETE FROM {GOLD}.fact_its_series"))
        conn.execute(text(f"DELETE FROM {GOLD}.fact_its_coef"))
        insert_df(conn, series.astype(object).where(series.notna(), None), GOLD, "fact_its_series")
        insert_df(conn, coefs, GOLD, "fact_its_coef")
    return fits


def report(fits: dict[str, Fit]) -> str:
    labels = {"share_value": "Participación de EE. UU. en el valor (pp) · PRINCIPAL",
              "share_tonnes": "Participación de EE. UU. en toneladas (pp) · robustez, desde 2016",
              "log_us_value": "log del valor de EE. UU. con control del resto (efecto % = e^b − 1) · robustez"}
    lines = ["# Serie de tiempo interrumpida · vísceras de EE. UU. en China", "",
             "Generado por `src/its.py`. Regresión segmentada con estacionalidad mensual y errores de Newey-West.",
             "Corte 1 = abr-2018 (represalias 232 y 301); corte 2 = feb-2020 (Fase Uno + exclusiones de la 301).",
             "Ene-feb 2020 se tratan como faltantes (hueco de reporte de EE. UU., supuesto #48).", ""]
    for k, f in fits.items():
        c = f.coef.set_index("term")
        lines += [f"## {labels[k]}", "", f"n = {f.n} meses · R² = {f.r2:.2f} · rezagos Newey-West = {f.lags}", "",
                  "| término | estimado | IC 95% | p |", "|---|---|---|---|"]
        for term, lab in (("trend", "tendencia previa (por mes)"), ("level_2018", "salto en abr-2018"),
                          ("slope_2018", "cambio de pendiente desde abr-2018 (por mes)"),
                          ("level_2020", "salto en feb-2020"), ("slope_2020", "cambio de pendiente desde feb-2020 (por mes)"),
                          ("log_rest_value", "control: log valor del resto")):
            if term in c.index:
                r = c.loc[term]
                lines.append(f"| {lab} | {r.estimate:+.3f} | [{r.ci_low:+.3f}; {r.ci_high:+.3f}] | {r.p:.3f} |")
        for cut, mlab in (("2018", "abr-2018"), ("2020", "feb-2020")):
            e, lo, hi = effect_after(f, cut, 12)
            pct = (f" → {100 * np.expm1(e):+.0f}% [{100 * np.expm1(lo):+.0f}%; {100 * np.expm1(hi):+.0f}%]"
                   if k == "log_us_value" else "")
            lines.append(f"\nEfecto a 12 meses de {mlab}: {e:+.2f} [{lo:+.2f}; {hi:+.2f}]{pct}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    print("=== Pork to China · Fase 14.2 · Serie de tiempo interrumpida ===\n")
    fits = run()
    txt = report(fits)
    from src.config import ROOT_DIR
    (ROOT_DIR / "docs" / "its.md").write_text(txt + "\n", encoding="utf-8")
    print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
