"""Página 9 · Recomendación: la decisión, los disparadores en semáforo y el pre-mortem."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from src.dashboard import data  # noqa: E402
from src.dashboard.theme import CHART_CONFIG, CONTEXT, INK, SERIES, STATUS, SURFACE, es, style  # noqa: E402
from src.recommendation import PREMORTEM, REFERENCE, decide  # noqa: E402

# Semáforo: reutiliza los colores e íconos de estado del tablero (siempre con ícono y texto, nunca solo color)
LIGHT = {"cumplido": STATUS["favorable"], "en camino": STATUS["en camino"], "no cumplido": STATUS["bloquea"]}
ROLE = {"economia": "Economía · basta una", "acceso": "Acceso · hacen falta las dos", "complementario": "Complementario"}

tr = data.triggers()
if tr.empty:
    st.warning("Sin disparadores: corre .\\pipeline.ps1 (etapa recommendation).")
    st.stop()
decision, why = decide(tr)
sm = data.mc_summary()
cert = sm[sm["cert_year"].notna()]

st.title(f"Recomendación: {decision}")
st.markdown(
    f"**{why}** Con los supuestos de hoy, el valor actual neto (VAN) de AgroPorc es negativo en "
    f"{(sm.npv_base < 0).sum()} de los {len(sm)} escenarios; el "
    f"Monte Carlo da una probabilidad de ganar de {es(100 * cert.p_npv_pos.min(), 0)}% a "
    f"{es(100 * cert.p_npv_pos.max(), 0)}% aun con certificación; y los países que entraron a China (Chile, Costa Rica, "
    "Brasil) ya eran libres de peste porcina clásica y tardaron unos 7 años desde el protocolo. La recomendación no "
    "es \"nunca\": es esperar y vigilar estas cinco condiciones. Los umbrales salen del modelo (VAN = 0), no de una "
    "opinión.")
st.caption(f"Regla: se revisa la inversión cuando se cumple una condición de economía y las dos de acceso. "
           f"Escenario de referencia: {REFERENCE} (caso comercial central, autosuficiencia china al alza, "
           f"certificación en el año 6). Actualizado el {pd.to_datetime(tr.as_of.iloc[0]):%d-%m-%Y}.")

cols = st.columns(len(tr))
for col, r in zip(cols, tr.itertuples()):
    color, icon, _ = LIGHT[r.status]
    with col:
        st.markdown(
            f"<div style='border-left:6px solid {color};padding:6px 10px;background:{SURFACE}'>"
            f"<div style='font-size:12px;color:#6b6a65'>{r.trigger_code} · {ROLE[r.role]}</div>"
            f"<div style='font-weight:600'>{r.name_es}</div>"
            f"<div style='font-size:20px'>{icon} {r.status.capitalize()}</div></div>", unsafe_allow_html=True)
        st.caption(f"**Condición:** {r.condition_es}  \n**Hoy:** {r.current_es}")

st.subheader("¿Qué tan lejos están los dos precios?")
left, right = st.columns(2)
for col, code, title, better in ((left, "D1", "Víscera en planta: hay que comprarla más barata", "≤"),
                                 (right, "D2", "FOB en China: tendría que subir", "≥")):
    r = tr.set_index("trigger_code").loc[code]
    fig = go.Figure()
    fig.add_shape(type="rect", x0=r.threshold_min, x1=r.threshold_max, y0=-0.35, y1=0.35,
                  fillcolor=CONTEXT, opacity=0.35, line_width=0)
    fig.add_trace(go.Scatter(x=[r.threshold], y=[0], mode="markers", name=f"Umbral {REFERENCE}",
                             marker=dict(symbol="line-ns", size=34, line=dict(width=3, color=INK)),
                             hovertemplate=f"Umbral {REFERENCE}: %{{x:.2f}} USD/kg<extra></extra>"))
    fig.add_trace(go.Scatter(x=[r.current_value], y=[0], mode="markers", name="Hoy",
                             marker=dict(size=16, color=SERIES[1], line=dict(color=SURFACE, width=2)),
                             hovertemplate="Hoy: %{x:.2f} USD/kg<extra></extra>"))
    gap = (r.threshold / r.current_value - 1) * 100
    fig.add_annotation(x=(r.threshold_min + r.threshold_max) / 2, y=0.42, text="rango de umbrales (6 escenarios)",
                       showarrow=False, font=dict(size=11, color=INK), yanchor="bottom")
    lo = min(r.current_value, r.threshold_min) - 0.1
    hi = max(r.current_value, r.threshold_max) + 0.1
    fig.update_layout(title=title)
    fig.update_xaxes(title="USD/kg", range=[lo, hi])
    fig.update_yaxes(visible=False, range=[-0.6, 0.9])
    with col:
        st.plotly_chart(style(fig, height=220, legend=True), width="stretch", config=CHART_CONFIG)
        st.caption(f"Hoy {es(r.current_value, 2)} USD/kg; condición: {better} {es(r.threshold, 2)}. "
                   f"Brecha: {es(abs(gap), 0)}% {'menos' if code == 'D1' else 'más'}. Cada umbral supone el otro precio en su valor base.")

st.subheader("Pre-mortem: es 2032 y el proyecto fracasó, ¿por qué?")
st.caption("Probabilidad e impacto son juicio del analista, no salen de un modelo. La señal y el lugar donde se vigila sí salen del proyecto.")
pm = pd.DataFrame(PREMORTEM)
grid = pd.DataFrame({p: [", ".join(pm[(pm.prob == p) & (pm.impact == i)].code) or "—" for i in ("alto", "medio")]
                     for p in ("baja", "media", "alta")}, index=["impacto alto", "impacto medio"])
grid.columns = ["prob. baja", "prob. media", "prob. alta"]
st.dataframe(grid, width=520)
rows = ["| | causa | prob. | impacto | disparador | señal temprana | dónde se vigila |", "|---|---|---|---|---|---|---|"]
rows += [f"| {r.code} | {r.cause_es} | {r.prob} | {r.impact} | {r.trigger} | {r.signal_es} | {r.watch_es} |" for r in pm.itertuples()]
st.markdown("\n".join(rows))
