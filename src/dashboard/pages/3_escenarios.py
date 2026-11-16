"""Página 3 · Los 24 escenarios: lo que define el negocio es certificar, y cuándo."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from src.dashboard import data  # noqa: E402
from src.dashboard.theme import CHART_CONFIG, DIVERGING, SERIES, es, style  # noqa: E402

st.title("Los 24 escenarios de AgroPorc")
sc = data.scenarios()
pos = int((sc["npv_usd"] > 0).sum())
cert = sc[sc["cert_year"].notna()]
delay = (cert.pivot_table(index=["trade_case", "china_selfsuff"], columns="cert_year", values="npv_usd"))
cost2 = (delay[2] - delay[4]).mean() / 1e6
st.markdown(
    f"**{pos} de 24 escenarios tienen VAN positivo**: todos los que logran el protocolo sanitario. Los 6 sin "
    f"certificación pierden la inversión completa. **Cada dos años de demora en certificar cuestan en promedio "
    f"{es(cost2, 1)} millones de USD de VAN**: el valor del proyecto está en conseguir el protocolo, y pronto.")

rows = [("A", "up"), ("A", "down"), ("B", "up"), ("B", "down"), ("C", "up"), ("C", "down")]
cols = [2, 4, 6, None]
ylab = {"A": "A · se cierra", "B": "B · statu quo", "C": "C · se abre"}
zlab = {"up": "China autoabastece", "down": "China importa más"}
z, txt = [], []
for tc, cs in rows:
    zr, tr = [], []
    for cy in cols:
        m = sc[(sc.trade_case == tc) & (sc.china_selfsuff == cs) &
               (sc.cert_year.isna() if cy is None else sc.cert_year == cy)].iloc[0]
        zr.append(m.npv_usd / 1e6)
        tr.append(("+" if m.npv_usd > 0 else "") + es(m.npv_usd / 1e6, 2) + " M")
    z.append(zr)
    txt.append(tr)
lim = max(abs(min(min(r) for r in z)), max(max(r) for r in z))
fig = go.Figure(go.Heatmap(
    z=z, x=list(range(4)), y=list(range(len(rows))),
    colorscale=DIVERGING, zmid=0, zmin=-lim, zmax=lim,
    xgap=2, ygap=2, colorbar=dict(title="VAN (M USD)", ticksuffix=" M"),
    customdata=[[f"{ylab[t]} · {zlab[c]} · " + ["certifica año 2", "año 4", "año 6", "nunca"][j] for j in range(4)]
                for t, c in rows],
    hovertemplate="%{customdata}<br>VAN %{z:.2f} millones USD<extra></extra>"))
# Texto blanco sobre las celdas oscuras, tinta oscura sobre las claras (contraste legible en ambas)
for i, (zr, tr) in enumerate(zip(z, txt)):
    for j, (v, t) in enumerate(zip(zr, tr)):
        fig.add_annotation(x=j, y=i, text=t, showarrow=False, font=dict(size=13, color="white" if abs(v) / lim > 0.55 else "#0b0b0b"))
fig.update_layout(title="VAN al 12% por escenario (millones de USD) · rojo = pierde, azul = gana")
fig.update_xaxes(tickvals=list(range(4)), ticktext=["Certifica año 2", "Año 4", "Año 6", "Nunca"])
fig.update_yaxes(autorange="reversed", showgrid=False, tickvals=list(range(len(rows))),
                 ticktext=[f"{ylab[t]} · {zlab[c]}" for t, c in rows])
st.plotly_chart(style(fig, height=430), width="stretch", config=CHART_CONFIG)

st.subheader("¿Cuándo se recupera la inversión?")
cf = data.cashflows()
options = sorted(sc["code"])
pick = st.multiselect("Compara hasta 3 escenarios", options, default=["B-up-2", "B-up-4", "B-up-6"], max_selections=3)
fig = go.Figure()
for code, color in zip(pick, SERIES):
    d = cf[cf["code"] == code]
    fig.add_scatter(x=d["year_n"], y=d["cumulative_dcf"] / 1e6, name=code, mode="lines+markers",
                    line=dict(color=color, width=2), marker=dict(size=8, color=color, line=dict(color="#fcfcfb", width=2)),
                    hovertemplate=code + " · año %{x}: %{y:.2f} M USD<extra></extra>")
fig.update_layout(title="Flujo de caja descontado acumulado (millones de USD; cruza el cero = se recuperó)")
fig.update_xaxes(title="Año del proyecto (0 = 2026)", dtick=1)
fig.update_yaxes(ticksuffix=" M")
st.plotly_chart(style(fig, legend=True), width="stretch", config=CHART_CONFIG)

with st.expander("Ver los 24 escenarios"):
    st.dataframe(sc.sort_values("npv_usd", ascending=False)[
        ["code", "label_es", "npv_usd", "irr_pct", "payback_years", "breakeven_offal_usd_kg", "fx_usd", "jobs"]
    ].round(2), hide_index=True)
st.caption("USD reales, año 0 = 2026, tasa 12%, impuesto efectivo 36,25%. Supuestos con fuente o marcados como tales "
           "en docs/assumptions.md.")
