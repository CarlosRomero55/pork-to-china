"""
test_dashboard.py · Fase 12 · cada página del tablero carga sin errores con los datos reales, y los
controles cambian lo que deben. Usa el probador oficial de Streamlit (AppTest), sin navegador.
Se omite si gold está vacío.
"""
from pathlib import Path

import pytest
from sqlalchemy import text

from src import simulation as sim
from src.db import get_engine

st_testing = pytest.importorskip("streamlit.testing.v1")
PAGES = Path(__file__).resolve().parents[1] / "src" / "dashboard" / "pages"


@pytest.fixture(scope="module", autouse=True)
def gold_ready():
    with get_engine("bi").connect() as c:
        if not c.execute(text("SELECT COUNT(*) FROM pork_gold.fact_scenario_result")).scalar():
            pytest.skip("gold vacío: corre primero .\\pipeline.ps1")


def run(page: str):
    at = st_testing.AppTest.from_file(str(PAGES / page), default_timeout=90).run()
    assert not at.exception, [e.value for e in at.exception]
    return at


@pytest.mark.parametrize("page,title", [
    ("1_ventana.py", "La ventana de China se está cerrando"),
    ("2_precio.py", "El precio en destino"),
    ("3_escenarios.py", "Los 24 escenarios de AgroPorc"),
    ("4_simulador.py", "Simulador What-If"),
])
def test_every_page_loads(page, title):
    assert run(page).title[0].value == title


def test_window_page_switches_product():
    at = run("1_ventana.py")
    at.radio[0].set_value("Carne").run()
    assert not at.exception and any("carne" in m.value for m in at.markdown)


def test_price_page_changes_with_trade_case():
    at = run("2_precio.py")
    before = [m.value for m in at.markdown if "Ecuador llegaría" in m.value][0]
    at.radio[1].set_value("A · se levantan las represalias").run()
    after = [m.value for m in at.markdown if "Ecuador llegaría" in m.value][0]
    assert not at.exception and before != after


def test_simulator_reacts_to_offal_value():
    at = run("4_simulador.py")
    npv_base = at.metric[0].value
    at.slider[0].set_value(1.5).run()                 # víscera muy cara → el VAN cae
    assert not at.exception and at.metric[0].value != npv_base and "no conviene" in " ".join(m.value for m in at.markdown)


def test_shared_simulation_matches_pipeline():
    """El tablero y la API usan src/simulation.py: sin cambios debe dar el VAN del pipeline."""
    for code in ("B-up-4", "C-down-2", "A-up-6"):
        base = sim.load(code)
        assert abs(sim.run(base).npv_usd - base.base_npv) < 1, code
    with pytest.raises(sim.UnknownScenario):
        sim.load("Z-9")
