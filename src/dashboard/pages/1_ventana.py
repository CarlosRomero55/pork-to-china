"""Página 1 · La ventana de China: el mercado se achica y los aranceles reparten lo que queda."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from src.dashboard import data  # noqa: E402
from src.dashboard.theme import CHART_CONFIG, CONTEXT, DIVERGING, SERIES, es, style  # noqa: E402

st.title("La ventana de China se está cerrando")
bal = data.china_balance()
sam = data.sam_yearly()
peak = bal.loc[bal["imports_kt"].idxmax()]
last = bal.iloc[-1]
sam25 = sam[sam["year"] == 2025].iloc[0]

st.markdown(
    f"China volvió a autoabastecerse tras la peste porcina de 2020: en {int(last.market_year)} importaría "
    f"**{es(last.imports_kt)} mil t**, apenas el **{es(100 * last.imports_kt / peak.imports_kt)}%** de lo que "
    f"importó en {int(peak.market_year)}. Lo que queda se reparte entre proveedores, y los aranceles de la "
    f"guerra comercial deciden quién gana espacio.")

c1, c2, c3 = st.columns(3)
c1.metric(f"Importaciones de China {int(last.market_year)} (proyección USDA)", f"{es(last.imports_kt)} mil t",
          f"{es(100 * (last.imports_kt / peak.imports_kt - 1))}% vs {int(peak.market_year)}", delta_color="off")
c2.metric(f"Autosuficiencia {int(last.market_year)}", f"{es(last.self_sufficiency_pct, 1)}%",
          f"+{es(last.self_sufficiency_pct - peak.self_sufficiency_pct, 1)} pp vs {int(peak.market_year)}",
          delta_color="off")
c3.metric("Mercado al alcance de Ecuador (SAM 2025)", f"{es(sam25.sam_tonnes / 1e6, 2)} millones de t",
          f"{es(sam25.sam_usd / 1e6)} MUSD FOB", delta_color="off")

left, right = st.columns(2)
with left:
    colors = [CONTEXT if p else SERIES[0] for p in bal["is_projection"]]
    fig = go.Figure(go.Bar(
        x=bal["market_year"], y=bal["imports_kt"], marker_color=colors, marker_line=dict(color="#fcfcfb", width=2),
        text=[es(v) for v in bal["imports_kt"]], textposition="outside", cliponaxis=False,
        hovertemplate="%{x}: %{y:,.0f} mil t CWE<extra></extra>"))
    fig.update_layout(title="Importaciones de China (miles de t CWE · gris = proyección)")
    st.plotly_chart(style(fig), width="stretch", config=CHART_CONFIG)
with right:
    fig = go.Figure(go.Scatter(
        x=bal["market_year"], y=bal["self_sufficiency_pct"], mode="lines+markers",
        line=dict(color=SERIES[0], width=2), marker=dict(size=8, color=SERIES[0], line=dict(color="#fcfcfb", width=2)),
        hovertemplate="%{x}: %{y:.1f}%<extra></extra>"))
    fig.update_layout(title="Autosuficiencia de China (producción / consumo)")
    fig.update_yaxes(range=[85, 100], ticksuffix="%")
    st.plotly_chart(style(fig), width="stretch", config=CHART_CONFIG)
st.caption("Fuente: USDA FAS, Production, Supply and Distribution (PSD).")

st.subheader("¿Quién ganó espacio tras el arancel a EE. UU.?")
group = st.radio("Producto", ["Vísceras", "Carne"], horizontal=True,
                 help="Vísceras es el nicho de Ecuador; carne, el mercado grande.")
div = data.trade_diversion(group)
top_loser = div.iloc[0]
top_winner = div.iloc[-1]
st.markdown(f"En **{group.lower()}**, el que más perdió fue **{top_loser.proveedor}** "
            f"({es(top_loser.cambio_pp, 1)} puntos de participación) y el que más ganó, **{top_winner.proveedor}** "
            f"(+{es(top_winner.cambio_pp, 1)}). Comparación: 12 meses antes vs 12 meses después de marzo de 2025.")
fig = go.Figure(go.Bar(
    y=div["proveedor"], x=div["cambio_pp"], orientation="h",
    marker_color=[DIVERGING[0][1] if v < 0 else DIVERGING[2][1] for v in div["cambio_pp"]],
    marker_line=dict(color="#fcfcfb", width=2),
    text=[("+" if v > 0 else "") + es(v, 1) + " pp" for v in div["cambio_pp"]], textposition="outside",
    cliponaxis=False, hovertemplate="%{y}: %{x:+.1f} pp<extra></extra>"))
fig.update_layout(title=f"Cambio de participación en las compras chinas de {group.lower()} (puntos porcentuales)")
span = div["cambio_pp"].abs().max()
fig.update_xaxes(zeroline=True, zerolinecolor="#8a8984", ticksuffix=" pp", showgrid=True, gridcolor="#e6e5e1",
                 range=[min(div["cambio_pp"].min(), 0) - 0.35 * span, max(div["cambio_pp"].max(), 0) + 0.35 * span])
fig.update_yaxes(showgrid=False)
st.plotly_chart(style(fig, height=420), width="stretch", config=CHART_CONFIG)
with st.expander("Ver la tabla"):
    st.dataframe(div.rename(columns={"t_antes": "t antes", "t_despues": "t después"}), hide_index=True)
st.caption("Fuente: UN Comtrade, datos espejo (lo que declaran los 12 exportadores). Rojo = pierde · azul = gana.")
