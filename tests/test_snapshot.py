"""
test_snapshot.py · Paso 16.3 · la copia pública de gold (data/snapshot/) alcanza para todo el tablero

1. La lista GOLD_OBJECTS cubre todas las tablas y vistas que consultan el tablero y la simulación.
2. Los parámetros :nombre se traducen bien a DuckDB.
3. Si existe la copia: cada consulta del tablero corre en modo snapshot, y cada página carga sin errores
   (AppTest, sin navegador). Así se comprueba lo mismo que verá la app publicada.
"""
import re
from pathlib import Path

import pytest

from src import gold_source as gs

ROOT = Path(__file__).resolve().parents[1]
FUENTES = [ROOT / "src" / "dashboard" / "data.py", ROOT / "src" / "simulation.py",
           ROOT / "sql" / "queries" / "q01_trade_diversion.sql", *sorted((ROOT / "src" / "dashboard" / "pages").glob("*.py"))]
HAY_COPIA = (gs.SNAPSHOT_DIR / "manifest.json").exists()


def test_la_lista_cubre_todo_lo_que_consulta_el_tablero():
    usados = set()
    for f in FUENTES:
        usados |= set(re.findall(r"(?:\{GOLD\}|pork_gold)\.(\w+)", f.read_text(encoding="utf-8")))
    faltan = usados - set(gs.GOLD_OBJECTS)
    assert not faltan, f"Agrega a GOLD_OBJECTS en src/gold_source.py: {sorted(faltan)}"


def test_sin_sql_exclusivo_de_mysql():
    """FIELD() y las comillas invertidas no existen en DuckDB: el tablero no debe usarlos."""
    for f in FUENTES:
        texto = f.read_text(encoding="utf-8")
        assert "FIELD(" not in texto, f"{f.name}: usa CASE en vez de FIELD()"


def test_parametros_a_duckdb():
    sql = "SELECT * FROM t WHERE a = :code AND b = :hs AND c::int = 1 AND d = ':no'"
    assert gs.to_duckdb(sql) == "SELECT * FROM t WHERE a = $code AND b = $hs AND c::int = 1 AND d = ':no'"


@pytest.fixture
def modo_copia(monkeypatch):
    if not HAY_COPIA:
        pytest.skip("no hay copia en data/snapshot/: ejecuta .\\snapshot.ps1")
    monkeypatch.setenv("PORK_DATA", "snapshot")


def test_cada_consulta_del_tablero_corre_con_la_copia(modo_copia):
    from src.dashboard import data

    sc = data.scenarios()
    assert len(sc) == 24
    for fn in (data.china_balance, data.sam_yearly, data.cashflows, data.province_pigs, data.sanitary,
               data.access_benchmark, data.policy_events, data.offal_monthly_us_vs_rest, data.its_coef,
               data.mc_summary, data.last_run, data.triggers):
        assert len(fn()) > 0, fn.__name__
    assert data.offal_local_value() > 0
    for grupo in ("Vísceras", "Carne"):
        assert len(data.trade_diversion(grupo)) > 0
    for caso in "ABC":
        for hs in ("020649", "020329"):
            assert len(data.landed_cost(f"{caso}-up-2", hs)) > 0, (caso, hs)
    for modelo in data.its_coef()["model"].unique():
        assert len(data.its_series(modelo)) > 0
    clave = int(data.mc_summary()["scenario_key"].iloc[0])
    assert len(data.mc_hist(clave)) > 0 and len(data.mc_tornado(clave)) > 0


def test_la_simulacion_da_el_van_del_pipeline_con_la_copia(modo_copia):
    from src import simulation as sim

    base = sim.load("B-up-4")
    assert sim.run(base).npv_usd == pytest.approx(base.base_npv, abs=1.0)


PAGINAS = sorted(p.name for p in (ROOT / "src" / "dashboard" / "pages").glob("*.py"))


@pytest.mark.parametrize("pagina", PAGINAS)
def test_cada_pagina_carga_con_la_copia(modo_copia, pagina):
    st_testing = pytest.importorskip("streamlit.testing.v1")
    at = st_testing.AppTest.from_file(str(ROOT / "src" / "dashboard" / "pages" / pagina), default_timeout=90).run()
    assert not at.exception, [e.value for e in at.exception]
