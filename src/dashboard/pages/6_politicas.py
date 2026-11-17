"""Página 6 · Rastreador de políticas: aranceles, acuerdos, protocolos y sanidad, junto a las importaciones."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402
from plotly.subplots import make_subplots  # noqa: E402

from src.dashboard import data  # noqa: E402
from src.dashboard.theme import CHART_CONFIG, CONTEXT, INK, SERIES, SURFACE, style  # noqa: E402

CATEGORIES = {"arancel": "Arancel", "acuerdo": "Acuerdo comercial", "protocolo": "Protocolo sanitario",
              "sanitario": "Estado sanitario", "mercado": "Apertura / primer envío"}
CUTS = {"corte_2018": ("2018-04-02", "Corte 2018"), "corte_2020": ("2020-01-15", "Corte 2020")}

st.title("Rastreador de políticas")
ev = data.policy_events()
ev["event_date"] = pd.to_datetime(ev["event_date"])
st.markdown(
    f"**{len(ev)} eventos** que movieron (o pueden mover) el comercio de cerdo hacia China, cada uno con su fuente. "
    "Los cambios de arancel se cargan solos desde la tabla de medidas; el resto se registra a mano. Las líneas "
    "punteadas son los **cortes de la serie de tiempo interrumpida** (paso 14.2) y la **peste porcina africana** en "
    "China es el control: subió la demanda china al mismo tiempo que los aranceles a EE. UU.")

chosen = st.pills("Tipos de evento", list(CATEGORIES), default=list(CATEGORIES), selection_mode="multi",
                  format_func=CATEGORIES.get)
since = st.toggle("Solo desde 2018 (período con datos mensuales)", value=True)
shown = ev[ev["category"].isin(chosen or [])]
if since:
    shown = shown[shown["event_date"] >= "2018-01-01"]

imp = data.offal_monthly_us_vs_rest()
imp["date"] = pd.to_datetime(imp["date"])
imp = imp[imp["complete"] == 1]

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.62, 0.38], vertical_spacing=0.06)
for who, color in (("Resto de proveedores", CONTEXT), ("EE. UU.", SERIES[0])):
    d = imp[imp["who"] == who]
    fig.add_scatter(x=d["date"], y=d["tonnes"] / 1000, name=who, mode="lines", line=dict(color=color, width=2),
                    hovertemplate=f"{who}<br>%{{x|%b %Y}}: %{{y:,.1f}} mil t<extra></extra>", row=1, col=1)
lanes = [CATEGORIES[c] for c in CATEGORIES if c in (chosen or [])]
for r in shown.itertuples():
    is_cut = isinstance(r.its_role, str) and r.its_role.startswith("corte")
    is_ctrl = r.its_role == "control"
    color = SERIES[1] if is_cut else (SERIES[2] if is_ctrl else INK)
    fig.add_scatter(x=[r.event_date], y=[CATEGORIES[r.category]], mode="markers", showlegend=False,
                    marker=dict(size=11 if (is_cut or is_ctrl) else 9, color=color, symbol="diamond",
                                line=dict(color=SURFACE, width=1.5)),
                    hovertemplate=(f"<b>{r.title_es}</b><br>{r.country_es} · %{{x|%d-%m-%Y}}"
                                   f"{' (fecha aproximada)' if r.date_precision != 'dia' else ''}"
                                   f"<br>{r.effect_es}<extra></extra>"), row=2, col=1)
for role, (day, label) in CUTS.items():
    fig.add_vline(x=pd.Timestamp(day).timestamp() * 1000, line=dict(color=SERIES[1], width=1.5, dash="dot"))
    fig.add_annotation(x=pd.Timestamp(day), y=0.99, yref="y domain", text=label, showarrow=False,
                       font=dict(color=INK, size=11), xanchor="left", xshift=4, bgcolor=SURFACE)
asf = pd.Timestamp("2018-08-03")
fig.add_vline(x=asf.timestamp() * 1000, line=dict(color=SERIES[2], width=1.5, dash="dot"))
fig.add_annotation(x=asf, y=0.88, yref="y domain", text="PPA (control)", showarrow=False,
                   font=dict(color=INK, size=11), xanchor="left", xshift=4, bgcolor=SURFACE)
fig.update_yaxes(title="mil t de vísceras", row=1, col=1, rangemode="tozero")
fig.update_yaxes(categoryorder="array", categoryarray=lanes[::-1], row=2, col=1, showgrid=False)
fig.update_layout(title="Importaciones chinas de vísceras de cerdo (espejo, meses completos) y eventos de política")
if since:
    fig.update_xaxes(range=[pd.Timestamp("2017-11-01"), imp["date"].max() + pd.DateOffset(months=3)])
st.plotly_chart(style(fig, height=640, legend=True), width="stretch", config=CHART_CONFIG)
st.caption("Rombo naranja = evento usado como corte de la serie de tiempo · rombo verde = control (PPA) · "
           "rombo negro = otros eventos. Pasa el mouse para ver el detalle.")

st.subheader("Eventos")
table = shown.sort_values("event_date", ascending=False).assign(
    fecha=lambda d: [f"{x:%d-%m-%Y}" if p == "dia" else (f"{x:%m-%Y}" if p == "mes" else f"{x:%Y}")
                     for x, p in zip(d["event_date"], d["date_precision"])],
    tipo=lambda d: d["category"].map(CATEGORIES))
st.dataframe(table[["fecha", "country_es", "tipo", "title_es", "effect_es", "url"]].rename(columns={
    "fecha": "Fecha", "country_es": "País", "tipo": "Tipo", "title_es": "Evento", "effect_es": "Efecto esperado",
    "url": "Fuente"}), hide_index=True,
    column_config={"Fuente": st.column_config.LinkColumn("Fuente", display_text="abrir")})
st.caption(
    f"⚠️ Hallazgo del rastreador: la represalia de la sección 301 (6-jul-2018, cerdo de EE. UU. al 62%) no estaba "
    f"en la tabla de aranceles del modelo, que usa 37% para EE. UU. en 2018. Desde marzo de 2020 los importadores "
    f"pueden pedir exclusión de la 301, así que el arancel efectivo depende de cada importador. No cambia el caso "
    f"de Ecuador, pero sí la comparación histórica con EE. UU.")
