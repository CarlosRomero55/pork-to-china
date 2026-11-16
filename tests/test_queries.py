"""
test_queries.py · Fase 9 · las consultas de negocio corren con el usuario de solo lectura y
cumplen reglas que se pueden comprobar (participaciones suman 100, tasas verificadas, etc.).
Se omiten si gold está vacío.
"""
import pytest
from sqlalchemy import text

from src import run_queries as rq
from src.db import get_engine

QUERIES = {name: sql for name, sql, _ in rq.load_queries()}


@pytest.fixture(scope="module")
def conn():
    with get_engine("bi").connect() as c:
        if not c.execute(text("SELECT COUNT(*) FROM pork_gold.fact_china_imports")).scalar():
            pytest.skip("gold vacío: corre primero .\\\\pipeline.ps1")
        yield c


def q(conn, prefix):
    name = next(n for n in QUERIES if n.startswith(prefix))
    return rq.run(conn, QUERIES[name])


def test_every_query_has_a_business_question_and_runs(conn):
    assert len(QUERIES) >= 6
    for name, sql, meta in rq.load_queries():
        assert {"Pregunta", "Técnica", "Fuente", "Lectura"} <= meta.keys(), name
        assert len(rq.run(conn, sql)) > 0, name


def test_bi_user_cannot_write(conn):
    with pytest.raises(Exception, match="denied"):
        conn.execute(text("DELETE FROM pork_gold.dim_scenario WHERE scenario_key = 0"))


def test_q01_shares_add_up_to_100(conn):
    df = q(conn, "q01")
    for col in ("part_antes", "part_despues"):
        sums = df.groupby("grupo")[col].sum().astype(float)
        assert ((sums - 100).abs() < 0.6).all(), (col, sums.to_dict())


def test_q02_one_leader_per_year(conn):
    df = q(conn, "q02")
    for year in [c for c in df.columns if c.isdigit()]:
        assert (df[year] == 1).sum() == 1


def test_q04_pareto_ends_at_100(conn):
    df = q(conn, "q04")
    assert float(df["acumulado_pct"].iloc[-1]) == pytest.approx(100, abs=0.1)
    assert df["acumulado_pct"].astype(float).is_monotonic_increasing


def test_q05_reproduces_verified_tariffs(conn):
    df = q(conn, "q05").set_index(["hs", "proveedor"])
    assert float(df.loc[("020649", "Estados Unidos"), "efectivo_min"]) == 47
    assert float(df.loc[("020649", "Chile"), "brecha_pp"]) == 0
    assert df.loc[("020649", "Ecuador"), "acceso"] == "NO"


def test_q06_peak_is_2020(conn):
    df = q(conn, "q06").set_index("año")
    assert float(df.loc[2020, "pct_del_pico"]) == 100
