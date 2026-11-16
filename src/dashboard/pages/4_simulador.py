"""Página 4 · Simulador What-If: mueve los supuestos y mira el VAN al instante."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import numpy as np  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from src import simulation as sim  # noqa: E402
from src.dashboard import data  # noqa: E402
from src.dashboard.theme import CHART_CONFIG, INK_3, SERIES, es, style  # noqa: E402

st.title("Simulador What-If")
st.markdown("Mueve los supuestos y el modelo recalcula el VAN con **las mismas funciones del pipeline y de la API** "
            "(src/simulation.py). Nada se guarda en la base.")


@st.cache_data(ttl=600, show_spinner=False)
def inputs(code: str) -> sim.ScenarioInputs:
    return sim.load(code)


codes = sorted(c for c, y in zip(data.scenarios()["code"], data.scenarios()["cert_year"]) if y == y and y is not None)
left, right = st.columns([1, 2])
with left:
    code = st.selectbox("Escenario de partida", codes, index=codes.index("B-up-4"),
                        help="A/B/C = caso comercial · up/down = autosuficiencia china · número = año de certificación")
    base = inputs(code)
    p = base.params
    offal = st.slider("Valor local de la víscera (USD/kg)", 0.0, 1.6, float(p["offal_local_value_usd_kg"]), 0.05,
                      help="Lo que vale la víscera en Ecuador: es el dato que no se pudo verificar.")
    fob = st.slider("Precio FOB de venta (USD/kg)", 1.0, 2.6, float(p["ecuador_fob_usd_kg_offal"]), 0.05)
    rate = st.slider("Tasa de descuento (%)", 8.0, 20.0, float(p["discount_rate"]), 0.5)
    cap = st.slider("Capacidad de AgroPorc (t/año)", 1000, 10000, int(p["agroporc_capacity_t"]), 500)
    capex = st.slider("Inversión (veces la base)", 0.5, 3.0, 1.0, 0.1)

r = sim.run(base, capex_factor=capex, discount_rate=rate, offal_local_value_usd_kg=offal, fob_usd_kg=fob,
            capacity_t=cap)
with right:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("VAN (M USD)", es(r.npv_usd / 1e6, 2), f"{es(r.delta_npv_usd / 1e6, 2)} vs base",
              help="Valor actual neto a la tasa elegida; la diferencia es contra el escenario sin cambios.")
    m2.metric("TIR", "—" if r.irr_pct is None else f"{es(r.irr_pct, 1)}%")
    m3.metric("Payback (años)", "nunca" if r.payback_years is None else es(r.payback_years, 1))
    m4.metric("Víscera máx. (USD/kg)", "—" if r.breakeven_offal_usd_kg is None else es(r.breakeven_offal_usd_kg, 2),
              help="Valor local de la víscera con el que el VAN es cero.")
    verdict = "conviene" if r.npv_usd > 0 else "no conviene"
    st.markdown(f"Con estos supuestos, exportar **{verdict}**: VAN de **{es(r.npv_usd)} USD** y "
                f"**{es(r.total_tonnes)} t** vendidas en 10 años.")

    grid = np.round(np.arange(0.0, 1.61, 0.05), 2)
    npv = [sim.run(base, capex_factor=capex, discount_rate=rate, offal_local_value_usd_kg=v, fob_usd_kg=fob,
                   capacity_t=cap).npv_usd / 1e6 for v in grid]
    fig = go.Figure(go.Scatter(x=grid, y=npv, mode="lines", line=dict(color=SERIES[0], width=2),
                               hovertemplate="víscera %{x:.2f} USD/kg → VAN %{y:.2f} M USD<extra></extra>"))
    fig.add_scatter(x=[offal], y=[r.npv_usd / 1e6], mode="markers", showlegend=False,
                    marker=dict(size=12, color=SERIES[1], line=dict(color="#fcfcfb", width=2)),
                    hovertemplate="tu supuesto: %{y:.2f} M USD<extra></extra>")
    if r.breakeven_offal_usd_kg is not None and 0 <= r.breakeven_offal_usd_kg <= 1.6:
        fig.add_vline(x=r.breakeven_offal_usd_kg, line=dict(color=INK_3, dash="dot", width=1),
                      annotation_text=f"equilibrio {es(r.breakeven_offal_usd_kg, 2)}", annotation_position="top")
    fig.update_layout(title="VAN según el valor local de la víscera (millones de USD; naranja = tu supuesto)")
    fig.update_xaxes(title="Valor local de la víscera (USD/kg)")
    fig.update_yaxes(ticksuffix=" M")
    st.plotly_chart(style(fig, height=380), width="stretch", config=CHART_CONFIG)
