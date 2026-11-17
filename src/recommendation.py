"""
Pork to China · Fase 15.1 · Disparadores de la recomendación

La recomendación es "no invertir hoy". Este módulo dice, en cada corrida del pipeline, qué tendría que
cambiar para revisarla y qué tan lejos estamos. Hay cinco disparadores:

  economía (basta UNO, con el otro en su valor base)
    D1  precio en planta de la víscera ≤ el que deja VAN = 0
    D2  FOB de Chile en vísceras 020649 (últimos 12 meses) ≥ el que deja VAN = 0
  acceso (hacen falta LOS DOS)
    D3  zona continental libre de peste porcina clásica reconocida por la OMSA
    D4  protocolo sanitario de cerdo Ecuador–China firmado con la GACC
  complementario (no decide, pero ayuda)
    D5  estatus de libre de fiebre aftosa sin vacunación

Los umbrales de D1 y D2 salen del modelo: VAN = 0 en el escenario de referencia B-up-6 (caso comercial
central, autosuficiencia china al alza, certificación en el año 6, el único horizonte creíble según el
benchmark de acceso) y el rango en los 6 escenarios con certificación en el año 6. No hay umbral inventado.

Estado de cada disparador:
  cumplido     el valor actual pasa el umbral de referencia (o la fuente lo da por logrado)
  en camino    pasa el umbral de algún escenario creíble (o hay un proceso en curso)
  no cumplido  el resto

Resultado en gold.fact_trigger y en docs/triggers.md.
Uso:  python -m src.recommendation
"""
from __future__ import annotations

import sys
from datetime import date

import numpy as np
import pandas as pd
from sqlalchemy import text

from src import monte_carlo as mc
from src.config import ROOT_DIR
from src.db import GOLD, SILVER, get_engine, insert_df
from src.finance import bisect
from src.scenarios import ramp_share

REPORT = ROOT_DIR / "docs" / "triggers.md"
PREMORTEM_DOC = ROOT_DIR / "docs" / "premortem.md"
REFERENCE = "B-up-6"
CERT_YEAR = 6
def n2(v: float) -> str:
    """Dos decimales con coma decimal."""
    return f"{v:.2f}".replace(".", ",")


RISK_TO_STATUS = {"favorable": "cumplido", "en camino": "en camino", "bloquea": "no cumplido"}

# Pre-mortem: "es 2032 y AgroPorc invirtió y fracasó, ¿por qué?". Probabilidad e impacto son JUICIO DEL
# ANALISTA (no salen de un modelo); la señal temprana y el lugar donde se vigila sí salen del proyecto.
PREMORTEM = (
    dict(code="R1", cause_es="Nunca llega la zona libre de peste porcina clásica (o llega después de 2032)",
         prob="alta", impact="alto", trigger="D3",
         signal_es="Vacunación por debajo de la meta (1.346.020 de 2.060.450 cerdos a jul-2026); brotes nuevos en provincias candidatas",
         watch_es="silver.sanitary_status · página 5"),
    dict(code="R2", cause_es="La víscera vale más en Ecuador que en China: el mercado local la absorbe",
         prob="alta", impact="alto", trigger="D1",
         signal_es="Precio de productor del cuero y las patitas (SIPA) por encima de 1,14 USD/kg en planta",
         watch_es="silver.assumption · página 4"),
    dict(code="R3", cause_es="Los precios FOB en China siguen bajando por sobreoferta de los grandes proveedores",
         prob="media", impact="alto", trigger="D2",
         signal_es="FOB de Chile en 020649 a la baja frente al año anterior y lejos del umbral de D2",
         watch_es="gold.fact_china_imports · página 2"),
    dict(code="R4", cause_es="Tregua duradera EE. UU.–China: el cerdo de EE. UU. recupera su lugar",
         prob="media", impact="alto", trigger="—",
         signal_es="Baja el arancel a las vísceras de EE. UU.; la serie de tiempo ya mostró +10,2 pp para EE. UU. tras las exclusiones de 2020",
         watch_es="gold.fact_tariff_applied · páginas 6 y 7"),
    dict(code="R5", cause_es="El protocolo con la GACC tarda más de 7 años (lo que tardaron Costa Rica y Brasil)",
         prob="alta", impact="medio", trigger="D4",
         signal_es="Sin proceso público iniciado con la GACC a fines de 2027",
         watch_es="silver.access_benchmark · página 5"),
    dict(code="R6", cause_es="AgroPorc no reúne 5.000 t de víscera de camales habilitados para exportar",
         prob="media", impact="alto", trigger="—",
         signal_es="Pocas plantas con registro sanitario en las provincias candidatas (Imbabura, Santo Domingo, Guayas, Carchi)",
         watch_es="silver.province_pigs · página 5"),
    dict(code="R7", cause_es="Entra la peste porcina africana a Ecuador y se cierran todos los mercados",
         prob="baja", impact="alto", trigger="—",
         signal_es="Brotes en países con comercio o vuelos directos (en 2025, casos en España según Agrocalidad)",
         watch_es="silver.sanitary_status · página 5"),
    dict(code="R8", cause_es="China produce más y compra menos cerdo importado",
         prob="media", impact="medio", trigger="—",
         signal_es="Importaciones chinas de USDA PSD a la baja dos años seguidos",
         watch_es="gold.fact_market_balance · página 1"),
)


# ---------------------------------------------------------------- umbrales del modelo
def thresholds(conn) -> pd.DataFrame:
    """Víscera y FOB que dejan VAN = 0 en cada escenario con certificación en el año 6."""
    sc, params, caps, _ = mc.load(conn)
    be = pd.read_sql(text(f"SELECT scenario_key, breakeven_offal_usd_kg FROM {GOLD}.fact_scenario_result"), conn)
    rows = []
    for s in sc[sc["cert_year"] == CERT_YEAR].itertuples():
        base = params[params["scenario_key"] == s.scenario_key].set_index("name")["value"].to_dict()
        cap = caps[s.scenario_key]
        ramps = np.array([ramp_share(y, CERT_YEAR, base["entry_ramp_y1_pct"], base["entry_ramp_y2_pct"])
                          for y in range(1, len(cap) + 1)])
        fob = bisect(lambda v: mc.npv_vectorized(base | {"ecuador_fob_usd_kg_offal": v}, ramps, cap)[0], 0.5, 6.0)
        rows.append({"code": s.code, "offal_be": float(be.set_index("scenario_key").loc[s.scenario_key].iloc[0]),
                     "fob_be": fob})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- valores actuales
def current_offal(conn) -> float:
    return float(conn.execute(text(f"""SELECT value_base FROM {SILVER}.assumption
        WHERE name = 'offal_local_value_usd_kg' ORDER BY version DESC LIMIT 1""")).scalar())


def current_fob(conn) -> tuple[float, int]:
    """FOB de Chile en vísceras 020649 a China, últimos 12 meses con dato (base espejo, sin atípicos)."""
    row = conn.execute(text(f"""
        WITH cl AS (
          SELECT f.date_key, f.tonnes, f.value_usd FROM {GOLD}.fact_china_imports f
          JOIN {GOLD}.dim_product p ON p.product_key = f.product_key AND p.hs_code = '020649'
          JOIN {GOLD}.dim_country c ON c.country_key = f.partner_key AND c.iso3 = 'CHL'
          WHERE f.basis = 'mirror' AND NOT f.is_outlier AND f.tonnes > 0)
        SELECT SUM(value_usd) / (1000 * SUM(tonnes)), MAX(date_key) FROM cl
        WHERE date_key > (SELECT MAX(date_key) FROM cl) - 10000""")).one()
    return float(row[0]), int(row[1])


def sanitary_status(conn, disease_like: str) -> tuple[str, str, str]:
    r = conn.execute(text(f"SELECT china_risk, status_es, source FROM {GOLD}.v_dash_sanitary WHERE disease LIKE :d"),
                     {"d": disease_like}).one()
    return RISK_TO_STATUS[r[0]], r[1], r[2]


def protocol_status(conn) -> tuple[str, str]:
    r = conn.execute(text(f"SELECT process_start, market_open, offal_access_es FROM {GOLD}.v_dash_access_benchmark "
                          "WHERE iso3 = 'ECU'")).one()
    if r[1] is not None:
        return "cumplido", f"Mercado abierto desde {int(r[1])}"
    if r[0] is not None:
        return "en camino", f"Proceso iniciado en {int(r[0])}; sin protocolo firmado"
    return "no cumplido", "Sin protocolo firmado ni proceso público iniciado con la GACC"


# ---------------------------------------------------------------- disparadores
def numeric_status(current: float, ref: float, lo: float, hi: float, higher_is_better: bool) -> str:
    if higher_is_better:
        return "cumplido" if current >= ref else "en camino" if current >= lo else "no cumplido"
    return "cumplido" if current <= ref else "en camino" if current <= hi else "no cumplido"


def build(conn) -> pd.DataFrame:
    th = thresholds(conn)
    ref = th.set_index("code").loc[REFERENCE]
    today = date.today()
    offal = current_offal(conn)
    fob, fob_month = current_fob(conn)
    ppc = sanitary_status(conn, "%clásica%")
    fmd = sanitary_status(conn, "%aftosa%")
    proto = protocol_status(conn)
    fm = str(fob_month)
    rows = [
        dict(trigger_code="D1", sort_order=1, role="economia", name_es="Precio en planta de la víscera",
             condition_es=f"Comprar la víscera en planta a {n2(ref.offal_be)} USD/kg o menos (VAN = 0 en {REFERENCE})",
             current_value=offal, threshold=ref.offal_be, threshold_min=th.offal_be.min(), threshold_max=th.offal_be.max(),
             unit="USD/kg", current_es=f"{n2(offal)} USD/kg (supuesto v2 con precios SIPA; validar en entrevista)",
             status=numeric_status(offal, ref.offal_be, th.offal_be.min(), th.offal_be.max(), False),
             source_es="Modelo: fact_scenario_result.breakeven_offal_usd_kg; valor actual: silver.assumption v2 (SIPA/MAG)",
             watch_es="silver.assumption · página 4 (simulador)"),
        dict(trigger_code="D2", sort_order=2, role="economia", name_es="Precio FOB de las vísceras en China",
             condition_es=f"FOB de referencia (Chile, 020649) de {n2(ref.fob_be)} USD/kg o más (VAN = 0 en {REFERENCE})",
             current_value=fob, threshold=ref.fob_be, threshold_min=th.fob_be.min(), threshold_max=th.fob_be.max(),
             unit="USD/kg", current_es=f"{n2(fob)} USD/kg (Chile, 12 meses hasta {fm[4:6]}-{fm[:4]})",
             status=numeric_status(fob, ref.fob_be, th.fob_be.min(), th.fob_be.max(), True),
             source_es="UN Comtrade, datos espejo (importaciones de China desde Chile, HS 020649)",
             watch_es="gold.fact_china_imports · página 2 (precio en destino)"),
        dict(trigger_code="D3", sort_order=3, role="acceso", name_es="Zona libre de peste porcina clásica",
             condition_es="La OMSA reconoce una zona continental de Ecuador libre de PPC",
             current_value=None, threshold=None, threshold_min=None, threshold_max=None, unit=None,
             current_es=ppc[1], status=ppc[0], source_es=ppc[2],
             watch_es="silver.sanitary_status · página 5 (mapa sanitario)"),
        dict(trigger_code="D4", sort_order=4, role="acceso", name_es="Protocolo sanitario con China",
             condition_es="Ecuador y la GACC firman el protocolo de carne y subproductos de cerdo",
             current_value=None, threshold=None, threshold_min=None, threshold_max=None, unit=None,
             current_es=proto[1], status=proto[0],
             source_es="Benchmark de acceso (silver.access_benchmark); Chile y Costa Rica tardaron ~7 años",
             watch_es="silver.access_benchmark · páginas 5 y 6"),
        dict(trigger_code="D5", sort_order=5, role="complementario", name_es="Fiebre aftosa sin vacunación",
             condition_es="La OMSA reconoce a Ecuador libre de fiebre aftosa sin vacunación",
             current_value=None, threshold=None, threshold_min=None, threshold_max=None, unit=None,
             current_es=fmd[1], status=fmd[0], source_es=fmd[2],
             watch_es="silver.sanitary_status · página 5 (mapa sanitario)"),
    ]
    df = pd.DataFrame(rows)
    df["as_of"] = today
    return df


def decide(triggers: pd.DataFrame) -> tuple[str, str]:
    """Regla de decisión: invertir solo si se cumple UN disparador de economía Y LOS DOS de acceso."""
    eco = (triggers.loc[triggers["role"] == "economia", "status"] == "cumplido").any()
    acc = (triggers.loc[triggers["role"] == "acceso", "status"] == "cumplido").all()
    if eco and acc:
        return "revisar la inversión", "Se cumplen la condición económica y las dos de acceso: toca actualizar el modelo y reabrir la decisión."
    missing = []
    if not eco:
        missing.append("una condición económica (D1 o D2)")
    if not acc:
        missing.append("las dos de acceso (D3 y D4)")
    return "no invertir hoy", "Faltan " + " y ".join(missing) + "."


def save(df: pd.DataFrame) -> None:
    with get_engine("etl").begin() as conn:
        conn.execute(text(f"DELETE FROM {GOLD}.fact_trigger"))
        insert_df(conn, df, GOLD, "fact_trigger")


def report(df: pd.DataFrame, th: pd.DataFrame) -> str:
    decision, why = decide(df)
    icon = {"cumplido": "✅", "en camino": "⏳", "no cumplido": "⛔"}
    lines = ["# Disparadores de la recomendación", "",
             f"Generado por `src/recommendation.py` el {df.as_of.iloc[0]:%Y-%m-%d}. Regla: se revisa la inversión cuando se "
             "cumple **una** condición económica (D1 o D2) **y las dos** de acceso (D3 y D4).", "",
             f"**Decisión hoy: {decision}.** {why}", "",
             "| | disparador | condición | hoy | estado | dónde se vigila |", "|---|---|---|---|---|---|"]
    for r in df.sort_values("sort_order").itertuples():
        lines.append(f"| {r.trigger_code} | {r.name_es} | {r.condition_es} | {r.current_es} | {icon[r.status]} {r.status} | {r.watch_es} |")
    lines += ["", "## Umbrales por escenario (certificación en el año 6, VAN = 0)", "",
              "Cada umbral supone el otro supuesto en su valor base (víscera 1,38 o FOB 1,60).", "",
              "| escenario | víscera máxima en planta (USD/kg) | FOB mínimo (USD/kg) |", "|---|---|---|"]
    for r in th.itertuples():
        lines.append(f"| {r.code}{' (referencia)' if r.code == REFERENCE else ''} | {n2(r.offal_be)} | {n2(r.fob_be)} |")
    return "\n".join(lines) + "\n"


def premortem_report() -> str:
    lines = ["# Pre-mortem de AgroPorc", "",
             "Ejercicio: *es 2032, AgroPorc invirtió en exportar vísceras a China y fracasó. ¿Por qué?* Generado por "
             "`src/recommendation.py`. **La probabilidad y el impacto son juicio del analista**, no salen de un modelo; "
             "la señal temprana y el lugar donde se vigila sí salen de los datos del proyecto.", "",
             "| | causa del fracaso | probabilidad | impacto | disparador | señal temprana | dónde se vigila |",
             "|---|---|---|---|---|---|---|"]
    for r in PREMORTEM:
        lines.append(f"| {r['code']} | {r['cause_es']} | {r['prob']} | {r['impact']} | {r['trigger']} | {r['signal_es']} | {r['watch_es']} |")
    lines += ["", "## Matriz de riesgo", "", "| impacto \\ probabilidad | baja | media | alta |", "|---|---|---|---|"]
    for imp in ("alto", "medio"):
        cells = [", ".join(r["code"] for r in PREMORTEM if r["prob"] == p and r["impact"] == imp) or "—"
                 for p in ("baja", "media", "alta")]
        lines.append(f"| **{imp}** | " + " | ".join(cells) + " |")
    lines += ["", "Lectura: los dos riesgos de la esquina alta-alta (R1 sanitario y R2 económico) son justo los que hoy "
              "frenan la inversión. Por eso la recomendación no es \"nunca\", sino \"no hoy\" y vigilar los disparadores.", ""]
    return "\n".join(lines)


def main() -> int:
    print("=== Pork to China · Fase 15.1 · Disparadores de la recomendación ===\n")
    with get_engine("etl").connect() as conn:
        df = build(conn)
        th = thresholds(conn)
    save(df)
    txt = report(df, th)
    REPORT.write_text(txt, encoding="utf-8")
    PREMORTEM_DOC.write_text(premortem_report(), encoding="utf-8")
    print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
