"""Página 2 · El precio en destino: cuánto le cuesta a un importador chino 1 kg según su origen."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

from src.dashboard import data  # noqa: E402
from src.dashboard.theme import CHART_CONFIG, SERIES, es, style  # noqa: E402

st.title("El precio en destino")
st.markdown("El importador chino compara el **costo puesto en China**: precio FOB + flete y seguro + arancel. "
            "Ecuador se modela como tomador de precio (vende al FOB de Chile) y con el arancel del acuerdo "
            "comercial del año en que empezaría a exportar.")

c1, c2 = st.columns(2)
product = c1.radio("Producto", ["Vísceras congeladas (020649)", "Carne congelada (020329)"], horizontal=True)
case = c2.radio("Caso comercial", ["A · se levantan las represalias", "B · statu quo", "C · suben las represalias"],
                index=1, horizontal=True)
hs = product[-7:-1]
code = f"{case[0]}-up-2"
df = data.landed_cost(code, hs)
df["label"] = [n + ("" if a else " (sin acceso)") for n, a in zip(df["supplier"], df["has_access"])]

ec = df[df["iso3"] == "ECU"].iloc[0]
access = df[df["has_access"].astype(bool)].sort_values("landed_usd_kg")
best = access.iloc[0]
rank = int((access["landed_usd_kg"] < ec.landed_usd_kg).sum()) + 1
st.markdown(
    f"Con el caso **{case}**, Ecuador llegaría a China a **{es(ec.landed_usd_kg, 2)} USD/kg**: "
    f"el **{rank}.º más barato** frente a los proveedores que hoy tienen acceso, a "
    f"{es(ec.landed_usd_kg - best.landed_usd_kg, 2)} USD/kg de **{best.supplier}** "
    f"({es(best.landed_usd_kg, 2)}). Pero Ecuador todavía **no tiene protocolo sanitario**: sin él, no puede vender.")

fig = go.Figure()
parts = [("fob_usd_kg", "Precio FOB"), ("freight_ins_usd_kg", "Flete y seguro"), ("duty_usd_kg", "Arancel")]
for (col, name), color in zip(parts, SERIES):
    fig.add_bar(y=df["label"], x=df[col], name=name, orientation="h", marker_color=color,
                marker_line=dict(color="#fcfcfb", width=2),
                hovertemplate="%{y} · " + name + ": %{x:.2f} USD/kg<extra></extra>")
fig.add_scatter(y=df["label"], x=df["landed_usd_kg"], mode="text", showlegend=False,
                text=[f"  {es(v, 2)}  ({es(t, 1)}% arancel)" for v, t in zip(df["landed_usd_kg"], df["total_duty_pct"])],
                textposition="middle right", hoverinfo="skip", cliponaxis=False)
fig.update_layout(barmode="stack", title=f"Costo puesto en China, {product.lower()} (USD/kg, sin IVA)")
fig = style(fig, height=420, legend=True)
fig.update_layout(legend_traceorder="normal")     # mismo orden que las barras: FOB → flete → arancel
fig.update_xaxes(range=[0, df["landed_usd_kg"].max() * 1.35], title="USD por kg")
fig.update_yaxes(showgrid=False)
st.plotly_chart(fig, width="stretch", config=CHART_CONFIG)

with st.expander("Ver la tabla"):
    st.dataframe(df[["supplier", "has_access", "fob_usd_kg", "freight_ins_usd_kg", "total_duty_pct",
                     "duty_usd_kg", "landed_usd_kg"]].sort_values("landed_usd_kg").round(3), hide_index=True)
st.caption("FOB: UN Comtrade espejo 2025. Flete: reefer de 40 pies por ruta (supuesto con rango; el orden de los "
           "proveedores no cambia en el mínimo ni en el máximo). Arancel efectivo vigente con historia SCD2.")
