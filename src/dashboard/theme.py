"""
theme.py · Estilo común de los gráficos (Plotly)

Paleta validada con el skill dataviz (scripts/validate_palette.js, modo claro, todos los pares):
  categórica: azul #2a78d6 · naranja #eb6834 · aqua #1baf7a (aqua < 3:1 de contraste → siempre con
  etiquetas visibles o tabla); diverging azul ↔ rojo con punto medio gris para valores con signo (VAN);
  gris para el contexto. Una sola escala por gráfico (nunca doble eje). Formato numérico en español.
"""
from __future__ import annotations

import plotly.graph_objects as go

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
INK_3 = "#8a8984"
GRID = "#e6e5e1"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]          # orden fijo, nunca ciclado
CONTEXT = "#b9b8b2"                                   # gris de contexto (no es una serie)
# Sin barra de herramientas de Plotly: se montaba sobre los títulos. El zoom sigue con la rueda/doble clic.
CHART_CONFIG = {"displayModeBar": False}
DIVERGING = [[0.0, "#c4312f"], [0.5, "#f0efec"], [1.0, "#1c5cab"]]   # rojo ↔ gris ↔ azul


def style(fig: go.Figure, height: int = 360, legend: bool = False) -> go.Figure:
    # Con leyenda, más margen arriba: la leyenda va entre el título y el gráfico, sin montarse
    fig.update_layout(
        height=height, margin=dict(l=8, r=16, t=78 if legend else 40, b=8),
        title=dict(y=0.98, yanchor="top", x=0, xanchor="left"),
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        font=dict(family="Inter, Segoe UI, sans-serif", size=13, color=INK_2),
        title_font=dict(size=15, color=INK),
        separators=",.",                                # decimales con coma, miles con punto
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.01, x=0, title=None),
        hoverlabel=dict(bgcolor="white", font_size=13, font_color=INK),
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID, tickfont=dict(color=INK_2), title_font=dict(color=INK_2))
    fig.update_yaxes(gridcolor=GRID, zeroline=True, zerolinecolor=INK_3, zerolinewidth=1, tickformat=",~r",
                     tickfont=dict(color=INK_2), title_font=dict(color=INK_2))
    return fig


def es(v: float, decimals: int = 0) -> str:
    """Número en formato español (1.234,5)."""
    return f"{v:,.{decimals}f}".replace(",", "_").replace(".", ",").replace("_", ".")
