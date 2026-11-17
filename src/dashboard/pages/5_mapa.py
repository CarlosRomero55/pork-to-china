"""Página 5 · Mapa sanitario: dónde está el cerdo de Ecuador y qué frena el acceso a China."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import plotly.graph_objects as go  # noqa: E402
from plotly.colors import sample_colorscale  # noqa: E402
import streamlit as st  # noqa: E402

from src.dashboard import data  # noqa: E402
from src.dashboard.theme import (CHART_CONFIG, CONTEXT, INK, SEQUENTIAL, SERIES, STATUS, SURFACE, es,  # noqa: E402
                                 style)

GEO = Path(__file__).resolve().parents[1] / "assets" / "ecuador_provinces.geojson"
BIG_SHARE, HIGH_BREED = 5.0, 75.0          # umbrales de "provincia candidata" (supuesto de lectura)


@st.cache_data(show_spinner=False)
def geojson() -> dict:
    return json.loads(GEO.read_text(encoding="utf-8"))


st.title("Mapa sanitario: dónde está el cerdo de Ecuador")
pp = data.province_pigs()
if pp.empty:
    st.warning("No hay datos de la ESPAC cargados. Descarga los tabulados del INEC en data/raw/inec y corre .\\pipeline.ps1")
    st.stop()
year = int(pp["survey_year"].iloc[0])
pp["candidate"] = (pp["share_year_pct"] >= BIG_SHARE) & (pp["breed_pct"] >= HIGH_BREED)
top = pp.sort_values("pigs_per_year", ascending=False)
cands = pp[pp["candidate"]].sort_values("pigs_per_year", ascending=False)
st.markdown(
    f"Las 5 provincias con más cerdos suman el **{es(top.head(5)['share_year_pct'].sum(), 0)}%** del país "
    f"(INEC, ESPAC {year}). Las que combinan **volumen y granjas tecnificadas** (≥{es(BIG_SHARE)}% de los cerdos y "
    f"≥{es(HIGH_BREED)}% de raza) son **{', '.join(cands['province_name'])}**: ahí podría estar una planta como "
    f"AgroPorc. Pero el freno no es provincial: **la peste porcina clásica está en todo el continente**; la OMSA "
    f"solo reconoce como libre a Galápagos.")

left, right = st.columns([3, 2])
with left:
    hover = [f"<b>{r.province_name}</b><br>{es(r.pigs_per_year)} cerdos al año ({es(r.share_year_pct, 1)}%)"
             f"<br>{es(r.breed_pct, 0)}% de raza · {r.region}" for r in pp.itertuples()]
    # Mapa dibujado como polígonos planos (lon/lat) con Scatter: no depende del CDN de Plotly para el
    # mapa base, así funciona sin internet. Ecuador está en el ecuador: lon/lat sin proyectar casi no deforma.
    vmax = float(pp["pigs_per_year"].max()) / 1000
    by_dpa = pp.set_index("dpa_code")
    fig = go.Figure()
    for feat in geojson()["features"]:
        dpa = feat["properties"]["dpa"]
        if dpa not in by_dpa.index:
            continue
        r = by_dpa.loc[dpa]
        color = sample_colorscale(SEQUENTIAL, (r.pigs_per_year / 1000) / vmax)[0]
        polys = [feat["geometry"]["coordinates"]] if feat["geometry"]["type"] == "Polygon" else feat["geometry"]["coordinates"]
        xs, ys = [], []
        for poly in polys:                       # solo el anillo exterior; las provincias no tienen huecos relevantes
            xs += [c[0] for c in poly[0]] + [None]
            ys += [c[1] for c in poly[0]] + [None]
        fig.add_scatter(x=xs, y=ys, fill="toself", fillcolor=color, mode="lines",
                        line=dict(color=SURFACE, width=1.2), hoveron="fills", showlegend=False,
                        name=r.province_name, text=hover[list(by_dpa.index).index(dpa)], hoverinfo="text")
    # Barra de color: un punto invisible que lleva la escala
    fig.add_scatter(x=[None], y=[None], mode="markers", showlegend=False, hoverinfo="skip",
                    marker=dict(colorscale=SEQUENTIAL, cmin=0, cmax=vmax, color=[0], showscale=True,
                                colorbar=dict(title="miles de<br>cerdos/año", thickness=12, len=0.7,
                                              ticksuffix=" mil")))
    fig.update_layout(title=f"Cerdos al año por provincia (miles) · INEC ESPAC {year}")
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False, scaleanchor="x", scaleratio=1)
    st.plotly_chart(style(fig, height=520), width="stretch", config=CHART_CONFIG)

with right:
    st.subheader("Estado sanitario (nacional)")
    for r in data.sanitary().itertuples():
        color, icon, label = STATUS[r.china_risk]
        st.markdown(
            f"<div style='border-left:4px solid {color};padding:6px 12px;margin-bottom:10px;color:{INK}'>"
            f"<b>{icon} {r.disease}</b> · {label}<br><span style='font-size:0.9em'>{r.status_es}</span><br>"
            f"<span style='font-size:0.8em;color:#52514e'>{r.source} · {r.as_of:%d-%m-%Y}</span></div>",
            unsafe_allow_html=True)
    st.caption("Los brotes por provincia no son públicos: el estado sanitario se muestra a nivel nacional.")

st.subheader("¿Volumen o tecnificación?")
fig = go.Figure()
for is_cand, color, name in ((False, CONTEXT, "Resto"), (True, SERIES[1], "Candidatas: volumen y granjas tecnificadas")):
    d = pp[pp["candidate"] == is_cand]
    fig.add_scatter(
        x=d["share_year_pct"], y=d["breed_pct"], mode="markers+text", name=name,
        text=d["province_name"].where(d["share_year_pct"] >= BIG_SHARE, ""), textposition="top center",
        textfont=dict(color=INK, size=12),
        marker=dict(size=11, color=color, line=dict(color=SURFACE, width=2)),
        customdata=d[["province_name", "pigs_per_year"]],
        hovertemplate="<b>%{customdata[0]}</b><br>%{x:.1f}% de los cerdos del país<br>%{y:.0f}% de raza"
                      "<br>%{customdata[1]:,.0f} cerdos al año<extra></extra>")
fig.add_hline(y=HIGH_BREED, line=dict(color=CONTEXT, width=1, dash="dot"))
fig.add_vline(x=BIG_SHARE, line=dict(color=CONTEXT, width=1, dash="dot"))
fig.update_layout(title="Participación en los cerdos del país vs. porcentaje de cerdos de raza (tecnificación)")
fig.update_xaxes(title="% de los cerdos al año del país", ticksuffix="%", rangemode="tozero")
fig.update_yaxes(title="% de cerdos de raza", ticksuffix="%", range=[0, 105])
st.plotly_chart(style(fig, height=420, legend=True), width="stretch", config=CHART_CONFIG)

st.subheader("¿Cómo entraron los que ya exportan cerdo a China?")
bm = data.access_benchmark()
done = bm[bm["first_export"].notna()]
yrs = done["years_to_first_export"].dropna()
st.markdown(
    f"Chile, Costa Rica y Brasil **ya eran libres de peste porcina clásica** (todo el país o una zona) cuando China "
    f"abrió el mercado. Costa Rica y Brasil tardaron **unos {es(yrs.mean(), 0)} años** desde el inicio del proceso "
    f"hasta el primer envío; Brasil entró **solo con sus zonas libres**. Para Ecuador, que aún vacuna contra la PPC "
    f"en el continente, certificar en 2 o 4 años parece poco realista: los escenarios creíbles son el año 6 o nunca.")
fig = go.Figure()
order = list(bm["country_es"])
for r in done.itertuples():
    start = r.process_start if r.process_start == r.process_start and r.process_start else r.market_open
    fig.add_scatter(x=[start, r.first_export], y=[r.country_es] * 2, mode="lines+markers", showlegend=False,
                    line=dict(color=SERIES[0], width=2), marker=dict(size=10, color=SERIES[0], line=dict(color=SURFACE, width=2)),
                    hovertemplate=f"<b>{r.country_es}</b><br>%{{x}}<extra></extra>")
    label = f"{int(r.years_to_first_export)} años" if r.years_to_first_export == r.years_to_first_export else "apertura y primer envío"
    fig.add_annotation(x=r.first_export, y=r.country_es, text=label, showarrow=False, xanchor="left", xshift=10,
                       font=dict(color=INK, size=12))
ecu = bm[bm["iso3"] == "ECU"].iloc[0]
# Proyección (supuesto): si Ecuador iniciara hoy y tardara lo mismo que Costa Rica y Brasil
start_ecu, proj = 2026, 2026 + int(round(yrs.mean()))
fig.add_scatter(x=[start_ecu, proj], y=[ecu.country_es] * 2, mode="lines+markers", showlegend=False,
                line=dict(color=CONTEXT, width=2, dash="dot"), marker=dict(size=10, color=CONTEXT, line=dict(color=SURFACE, width=2)),
                hovertemplate="Ecuador (supuesto): inicio %{x}<extra></extra>")
fig.add_annotation(x=start_ecu, y=ecu.country_es, showarrow=False, xanchor="right", xshift=-10,
                   text=f"sin protocolo · si empieza hoy: ~{proj} (supuesto: {int(round(yrs.mean()))} años)",
                   font=dict(color=INK, size=12))
fig.update_layout(title="Del inicio del proceso sanitario al primer envío de cerdo a China")
fig.update_xaxes(dtick=2, range=[2003, 2036], showgrid=True, gridcolor="#e6e5e1")
fig.update_yaxes(categoryorder="array", categoryarray=order[::-1], showgrid=False)
st.plotly_chart(style(fig, height=300), width="stretch", config=CHART_CONFIG)
st.dataframe(bm[["country_es", "csf_status_es", "fmd_status_es", "offal_access_es", "lesson_es"]].rename(columns={
    "country_es": "País", "csf_status_es": "Peste porcina clásica", "fmd_status_es": "Fiebre aftosa",
    "offal_access_es": "Vísceras", "lesson_es": "Lección"}), hide_index=True)

with st.expander("Ver las 23 provincias"):
    st.dataframe(top[["province_name", "region", "pigs_per_year", "share_year_pct", "stock_head", "breed_pct",
                      "sales_q3_head"]].rename(columns={
        "province_name": "Provincia", "region": "Región", "pigs_per_year": "Cerdos al año",
        "share_year_pct": "% del país", "stock_head": "Existencia", "breed_pct": "% de raza",
        "sales_q3_head": "Ventas jul–sep"}), hide_index=True)
st.caption(
    f"Fuente: INEC, ESPAC {year} (tabulados T57–T59). La ESPAC es una encuesta a fincas: cuenta "
    f"{es(pp['pigs_per_year'].sum() / 1e6, 2)} millones de cerdos al año, mientras ASPE reporta unos 5,5 millones "
    "beneficiados, porque las granjas industriales grandes quedan subrepresentadas. Úsala para comparar provincias, "
    "no para el volumen nacional. Mapa: límites provinciales del INEC (2015) vía ec-atlas (licencia MIT).")
