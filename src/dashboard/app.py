"""
app.py · Fase 12 · Tablero de Pork to China (Streamlit)

Siete páginas: la ventana de China, el precio en destino, los escenarios, el simulador What-If, el
mapa sanitario, el rastreador de políticas y la serie de tiempo interrumpida.
Lee pork_gold con el usuario de solo lectura (pork_bi); el simulador usa src/simulation.py, la misma
función que la API, así el cálculo vive en un solo lugar.

Levantarlo:  streamlit run src/dashboard/app.py      (o .\\dashboard.ps1)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

st.set_page_config(page_title="Pork to China", page_icon="🐖", layout="wide")

PAGES = Path(__file__).parent / "pages"
nav = st.navigation([
    st.Page(PAGES / "1_ventana.py", title="1 · La ventana de China", default=True),
    st.Page(PAGES / "2_precio.py", title="2 · El precio en destino"),
    st.Page(PAGES / "3_escenarios.py", title="3 · Los 24 escenarios"),
    st.Page(PAGES / "4_simulador.py", title="4 · Simulador What-If"),
    st.Page(PAGES / "5_mapa.py", title="5 · Mapa sanitario"),
    st.Page(PAGES / "6_politicas.py", title="6 · Rastreador de políticas"),
    st.Page(PAGES / "7_serie_tiempo.py", title="7 · Serie de tiempo"),
])

with st.sidebar:
    st.markdown("**Pork to China**  \n¿Puede Ecuador aprovechar la guerra comercial?")
    st.caption("AgroPorc Ecuador es una empresa ficticia. Datos públicos: UN Comtrade, USDA PSD, "
               "aranceles de China con historia SCD2. Proyecto de portafolio de Carlos Romero.")
    try:
        from src.dashboard import data
        run = data.last_run()
        if len(run):
            st.caption(f"Última corrida del pipeline: n.º {int(run.run_id[0])} · {run.status[0]} · "
                       f"{run.finished_at[0]:%Y-%m-%d %H:%M}" if run.finished_at[0] is not None else "en curso")
    except Exception as e:                       # sin base de datos el tablero lo dice en vez de caerse
        st.error(f"No hay conexión con la base de datos ({type(e).__name__}). Corre .\\pipeline.ps1 y revisa el .env")

nav.run()
