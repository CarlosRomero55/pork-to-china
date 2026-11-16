"""
test_pipeline.py · Fase 8 · orquestación.
Usa etapas falsas (pequeños comandos de Python) y un candado propio, para no chocar con una
corrida real ni ejecutar el pipeline de verdad. Las corridas de prueba se borran al terminar.
"""
import pytest
from sqlalchemy import text

from src import pipeline as pl
from src.db import BRONZE, get_engine

LOCK = "pork_to_china_pipeline_pytest"
OK = pl.Stage("uno", ("-c", "print('hola desde la etapa 1')"), "Etapa uno")
FAIL = pl.Stage("dos", ("-c", "import sys; print('algo salió mal'); sys.exit(3)"), "Etapa dos")
THIRD = pl.Stage("tres", ("-c", "print('no debería correr')"), "Etapa tres")


@pytest.fixture(autouse=True)
def cleanup():
    yield
    with get_engine("etl").begin() as c:
        c.execute(text(f"DELETE FROM {BRONZE}.etl_run WHERE trigger_src = 'pytest'"))   # cascada a etapas


def run(stages):
    return pl.run_pipeline(stages, trigger="pytest", lock_name=LOCK, do_migrate=False, echo=lambda *a, **k: None)


def test_successful_run_is_recorded():
    res = run([OK])
    assert res.status == "ok"
    with get_engine("etl").connect() as c:
        row = c.execute(text(f"SELECT status, finished_at FROM {BRONZE}.etl_run WHERE run_id=:r"),
                        {"r": res.run_id}).one()
        st = c.execute(text(f"SELECT status, exit_code, output_tail FROM {BRONZE}.etl_run_stage "
                            f"WHERE run_id=:r"), {"r": res.run_id}).one()
    assert row.status == "ok" and row.finished_at is not None
    assert (st.status, st.exit_code) == ("ok", 0) and "hola desde la etapa 1" in st.output_tail


def test_stops_at_first_failure_and_skips_the_rest():
    res = run([OK, FAIL, THIRD])
    assert res.status == "failed"
    assert [(s.stage, s.status) for s in res.stages] == [("uno", "ok"), ("dos", "failed"), ("tres", "skipped")]
    assert res.stages[1].exit_code == 3 and "algo salió mal" in res.stages[1].tail


def test_lock_prevents_concurrent_runs():
    with get_engine("etl").connect() as other:
        assert other.execute(text("SELECT GET_LOCK(:n, 0)"), {"n": LOCK}).scalar() == 1
        try:
            with pytest.raises(RuntimeError, match="otra corrida"):
                run([OK])
        finally:
            other.execute(text("SELECT RELEASE_LOCK(:n)"), {"n": LOCK})


def test_dead_run_is_marked_aborted_by_the_next_one():
    with get_engine("etl").begin() as c:
        dead = c.execute(text(f"INSERT INTO {BRONZE}.etl_run (trigger_src, stages) VALUES ('pytest', 'x')")).lastrowid
    run([OK])
    with get_engine("etl").connect() as c:
        assert c.execute(text(f"SELECT status FROM {BRONZE}.etl_run WHERE run_id=:r"), {"r": dead}).scalar() == "aborted"


def test_stage_selection():
    names = lambda st: [s.name for s in st]
    assert "extract_comtrade" not in names(pl.select_stages(False, None))
    assert names(pl.select_stages(True, None))[:2] == ["extract_comtrade", "extract_psd"]
    assert names(pl.select_stages(False, "validate")) == ["validate", "gold", "queries", "landed_cost", "scenarios", "finance", "tests"]
    with pytest.raises(SystemExit):
        pl.select_stages(False, "no_existe")
