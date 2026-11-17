"""Página 8 · Monte Carlo: probabilidad de VAN positivo y qué supuesto pesa más."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from src.dashboard import data  # noqa: E402
from src.dashboard.theme import CHART_CONFIG, CONTEXT, DIVERGING, INK, SERIES, SURFACE, es, style  # noqa: E402

RED, BLUE = DIVERGING[0][1], DIVERGING[2][1]

st.title("Monte Carlo: ¿qué tan probable es ganar?")
sm = data.mc_summary()
if sm.empty:
    st.warning("Sin resultados: corre .\\pipeline.ps1 (etapa monte_carlo).")
    st.stop()
cert = sm[sm["cert_year"].notna()]
n = int(sm["n_draws"].iloc[0])
st.markdown(
    f"En vez de fijar cada supuesto en su valor base, se sortean **{es(n)} combinaciones** de 12 supuestos de costo, "
    f"precio y capacidad (distribución triangular mínimo–base–máximo) y se calcula el VAN de cada una, en los 24 "
    f"escenarios. Con certificación, la **probabilidad de VAN positivo va de {es(100 * cert.p_npv_pos.min(), 0)}% a "
    f"{es(100 * cert.p_npv_pos.max(), 0)}%**; sin certificación es 0%. El VAN típico (mediana) es peor que el de los "
    "valores base porque el rango del valor local de la víscera es asimétrico: hay más espacio para que suba que "
    "para que baje.")

codes = list(sm.sort_values("p_npv_pos", ascending=False)["code"])
code = st.selectbox("Escenario", codes, index=codes.index("B-up-4") if "B-up-4" in codes else 0)
row = sm[sm["code"] == code].iloc[0]
k1, k2, k3, k4 = st.columns(4)
k1.metric("P(VAN > 0)", f"{es(100 * row.p_npv_pos, 1)}%", delta_color="off")
k2.metric("VAN mediano (M USD)", es(row.npv_p50 / 1e6, 2), delta_color="off")
k3.metric("Rango 90% (M USD)", f"{es(row.npv_p05 / 1e6, 1)} a {es(row.npv_p95 / 1e6, 1)}", delta_color="off",
          help="Del percentil 5 al 95 de los sorteos")
k4.metric("VAN base (M USD)", es(row.npv_base / 1e6, 2), delta_color="off")

left, right = st.columns(2)
with left:
    h = data.mc_hist(int(row.scenario_key))
    mid = (h["bin_from"] + h["bin_to"]) / 2 / 1e6
    fig = go.Figure(go.Bar(
        x=mid, y=h["n"] / n * 100, width=(h["bin_to"] - h["bin_from"]) / 1e6 * 0.92,
        marker_color=[BLUE if v > 0 else RED for v in mid], marker_line_width=0,
        hovertemplate="VAN ≈ %{x:.2f} M USD<br>%{y:.1f}% de los sorteos<extra></extra>"))
    fig.add_vline(x=0, line=dict(color=INK, width=1))
    fig.add_vline(x=row.npv_base / 1e6, line=dict(color=CONTEXT, width=2, dash="dash"))
    fig.add_annotation(x=row.npv_base / 1e6, y=0.98, yref="y domain", text="valores base", showarrow=False,
                       xanchor="left", xshift=4, font=dict(color=INK, size=11), bgcolor=SURFACE)
    fig.update_layout(title=f"Distribución del VAN · {code} (millones de USD)", bargap=0)
    fig.update_xaxes(title="VAN (M USD)")
    fig.update_yaxes(title="% de los sorteos", ticksuffix="%")
    st.plotly_chart(style(fig, height=380), width="stretch", config=CHART_CONFIG)
with right:
    t = data.mc_tornado(int(row.scenario_key))
    base = row.npv_base / 1e6
    fig = go.Figure()
    for col, name, color in (("npv_at_min", "Supuesto en su mínimo", SERIES[0]), ("npv_at_max", "Supuesto en su máximo", SERIES[1])):
        fig.add_bar(y=t["label_es"], x=t[col] / 1e6 - base, base=base, orientation="h", name=name,
                    marker_color=color, marker_line=dict(color=SURFACE, width=1),
                    customdata=t[col] / 1e6, hovertemplate="%{y}<br>VAN: %{customdata:.2f} M USD<extra>" + name + "</extra>")
    fig.add_vline(x=base, line=dict(color=INK, width=1))
    fig.add_vline(x=0, line=dict(color=CONTEXT, width=1, dash="dot"))
    fig.update_layout(title=f"Qué supuesto mueve más el VAN · {code} (línea negra = base)", barmode="overlay")
    fig.update_xaxes(title="VAN (M USD)")
    st.plotly_chart(style(fig, height=380, legend=True), width="stretch", config=CHART_CONFIG)
top = t.sort_values("swing", ascending=False).iloc[0]
st.caption(f"El supuesto que más pesa es **{top.label_es.lower()}**: llevarlo de su mínimo a su máximo mueve el VAN "
           f"{es(top.swing / 1e6, 1)} millones de USD (correlación de Spearman con el VAN: {es(top.spearman, 2)}). "
           "Por eso validar ese precio en la entrevista vale más que afinar cualquier otro supuesto.")

st.subheader("Probabilidad de VAN positivo por escenario")
s2 = sm.sort_values("p_npv_pos")
fig = go.Figure(go.Bar(
    y=s2["code"], x=100 * s2["p_npv_pos"], orientation="h",
    marker_color=[CONTEXT if c != c else SERIES[0] for c in s2["cert_year"]], marker_line=dict(color=SURFACE, width=1),
    text=[f"{es(100 * v, 1)}%" for v in s2["p_npv_pos"]], textposition="outside", textfont=dict(color=INK),
    hovertemplate="%{y}: %{x:.1f}%<extra></extra>"))
fig.update_layout(title="P(VAN > 0) · gris = sin certificación")
fig.update_xaxes(title="probabilidad (%)", ticksuffix="%", range=[0, max(15, 100 * s2.p_npv_pos.max() * 1.25)])
st.plotly_chart(style(fig, height=640), width="stretch", config=CHART_CONFIG)
st.caption("Limitaciones: los supuestos se sortean de forma independiente (en la realidad el flete y el precio FOB "
           "podrían moverse juntos); la tasa de descuento queda fija en 12% porque es una decisión del inversionista; "
           "los supuestos de mercado definen cada escenario y no se sortean. Detalle en docs/monte_carlo.md.")
