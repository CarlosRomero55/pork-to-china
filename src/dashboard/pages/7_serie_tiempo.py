"""Página 7 · Serie de tiempo interrumpida: ¿la guerra comercial cambió la participación de EE. UU.?"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from src.dashboard import data  # noqa: E402
from src.dashboard.theme import CHART_CONFIG, CONTEXT, INK, SERIES, SURFACE, es, style  # noqa: E402

MODELS = {"share_value": "Participación en el valor (principal)",
          "share_tonnes": "Participación en toneladas (desde 2016)",
          "log_us_value": "Valor de EE. UU. controlando por el resto (log)"}
CUTS = {"2018": (pd.Timestamp("2018-04-01"), "Represalias"),
        "2020": (pd.Timestamp("2020-02-01"), "Fase Uno")}

st.title("Serie de tiempo interrumpida")
co = data.its_coef()
if co.empty:
    st.warning("Sin resultados: corre .\\pipeline.ps1 (etapa its).")
    st.stop()
c = co[co["model"] == "share_value"].set_index("term")


def ci(term: str, d: int = 1) -> str:
    r = c.loc[term]
    return f"{es(r.estimate, d)} pp (IC 95%: {es(r.ci_low, d)} a {es(r.ci_high, d)}; p = {es(r.p, 3)})"


st.markdown(
    "¿La guerra comercial cambió la **participación de EE. UU. en las vísceras de cerdo que compra China**, más "
    "allá de la tendencia y la estacionalidad que ya traía? Regresión segmentada con datos espejo mensuales desde "
    "2015, dos cortes y errores de Newey-West. La participación neutraliza la peste porcina africana (ago-2018), "
    "que subió la demanda china para todos los proveedores a la vez.")
k1, k2, k3 = st.columns(3)
k1.metric("Salto en abr-2018", f"{es(c.loc['level_2018', 'estimate'], 1)} pp", delta_color="off",
          help=ci("level_2018"))
k2.metric("Salto en feb-2020", f"+{es(c.loc['level_2020', 'estimate'], 1)} pp", delta_color="off",
          help=ci("level_2020"))
k3.metric("Meses analizados", f"{int(c['n_obs'].iloc[0])}", delta_color="off",
          help=f"R² = {es(c['r2'].iloc[0], 2)} · {int(c['nw_lags'].iloc[0])} rezagos de Newey-West")
st.markdown(
    f"**Lectura:** con las represalias de 2018, EE. UU. perdió de golpe **{es(-c.loc['level_2018', 'estimate'], 1)} "
    f"puntos** de participación (p = {es(c.loc['level_2018', 'p'], 3)}); con la Fase Uno y las exclusiones de la "
    f"sección 301 los recuperó (**+{es(c.loc['level_2020', 'estimate'], 1)} pp**, p = {es(c.loc['level_2020', 'p'], 3)}). "
    "Los aranceles movieron la participación por **escalones**, no por cambios de tendencia: el mercado se reparte "
    "rápido cuando cambia el arancel. Para Ecuador, el precio relativo puesto en destino sí importa.")

model = st.segmented_control("Medida", list(MODELS), default="share_value", format_func=MODELS.get) or "share_value"
s = data.its_series(model)
s["date"] = pd.to_datetime(s["date"])
is_log = model == "log_us_value"
unit = "log del valor" if is_log else "% de participación"
fig = go.Figure()
obs = s[~s["is_gap"].astype(bool)]
fig.add_scatter(x=obs["date"], y=obs["observed"], mode="markers", name="Observado",
                marker=dict(size=6, color=SERIES[0], line=dict(color=SURFACE, width=1)),
                hovertemplate="%{x|%b %Y}: %{y:.1f}<extra>Observado</extra>")
for seg_start, seg_end in ((None, CUTS["2018"][0]), (CUTS["2018"][0], CUTS["2020"][0]), (CUTS["2020"][0], None)):
    seg = s[((s["date"] >= seg_start) if seg_start is not None else True) & ((s["date"] < seg_end) if seg_end is not None else True)]
    fig.add_scatter(x=seg["date"], y=seg["fitted"], mode="lines", line=dict(color=SERIES[1], width=2),
                    name="Modelo", showlegend=seg_start is None, hoverinfo="skip")
post = s[s["date"] >= CUTS["2018"][0]]
fig.add_scatter(x=post["date"], y=post["counterfactual"], mode="lines", name="Sin guerra comercial (contrafactual)",
                line=dict(color=CONTEXT, width=2, dash="dash"), hoverinfo="skip")
gap = s[s["is_gap"].astype(bool)]
if not gap.empty:
    fig.add_vrect(x0=gap["date"].min() - pd.Timedelta(days=15), x1=gap["date"].max() + pd.Timedelta(days=15),
                  fillcolor=CONTEXT, opacity=0.25, line_width=0)
for day, label in CUTS.values():
    fig.add_vline(x=day.timestamp() * 1000, line=dict(color=INK, width=1, dash="dot"))
    fig.add_annotation(x=day, y=0.99, yref="y domain", text=label, showarrow=False, xanchor="left", xshift=4,
                       font=dict(color=INK, size=11), bgcolor=SURFACE)
fig.update_layout(title=f"EE. UU. en las importaciones chinas de vísceras de cerdo · {MODELS[model].lower()}")
fig.update_yaxes(title=unit, ticksuffix="" if is_log else "%", rangemode="normal" if is_log else "tozero")
st.plotly_chart(style(fig, height=460, legend=True), width="stretch", config=CHART_CONFIG)
st.caption("Puntos = meses observados · línea naranja = modelo con los dos cortes · línea gris = lo que habría "
           "seguido la tendencia sin cortes. Banda gris: ene–feb 2020, hueco de reporte de EE. UU. tratado como "
           "faltante (supuesto #48).")

st.subheader("Los tres modelos")
terms = {"level_2018": "Salto abr-2018", "slope_2018": "Cambio de pendiente abr-2018 (por mes)",
         "level_2020": "Salto feb-2020", "slope_2020": "Cambio de pendiente feb-2020 (por mes)"}
rows = []
for m, lab in MODELS.items():
    cm = co[co["model"] == m].set_index("term")
    for t, tl in terms.items():
        r = cm.loc[t]
        rows.append({"Modelo": lab, "Término": tl, "Estimado": es(r.estimate, 3),
                     "IC 95%": f"{es(r.ci_low, 2)} a {es(r.ci_high, 2)}", "p": es(r.p, 3),
                     "Significativo (5%)": "sí" if r.p < 0.05 else "no"})
st.dataframe(pd.DataFrame(rows), hide_index=True)
lv = co[(co["model"] == "log_us_value")].set_index("term")
st.caption(
    f"En el modelo en log, el salto de 2018 equivale a {es(100 * np.expm1(lv.loc['level_2018', 'estimate']), 0)}% del "
    f"valor exportado por EE. UU. y el de 2020 a +{es(100 * np.expm1(lv.loc['level_2020', 'estimate']), 0)}%. "
    "En toneladas el salto de 2018 se confirma y el de 2020 no es significativo: EE. UU. recuperó más valor que "
    "volumen. Limitaciones: 39 meses antes del primer corte; EE. UU. no reportó el peso en 2015; los cortes son "
    "cercanos a la PPA (por eso la medida principal es una participación); la escalada de abril de 2025 (125%) "
    "se ve como una caída puntual pero no se modela como corte. Detalle en docs/its.md.")
