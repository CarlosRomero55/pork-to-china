"""
test_scenarios.py · Fase 10.2 · mercado por escenario (TAM–SAM–SOM).
Las reglas se prueban sin base de datos; al final, pruebas sobre lo que quedó en gold.
"""
from datetime import date

import pandas as pd
import pytest
from sqlalchemy import text

from src import scenarios as sc
from src.db import get_engine


@pytest.mark.parametrize("year_n,cert,expected", [
    (1, 2, 0.0), (2, 2, 0.4), (3, 2, 0.7), (4, 2, 1.0), (10, 2, 1.0),   # rampa 40-70-100 desde el año 2
    (5, 6, 0.0), (6, 6, 0.4), (10, None, 0.0),                          # nunca certifica → 0
])
def test_ramp(year_n, cert, expected):
    assert sc.ramp_share(year_n, cert, 40, 70) == expected


def test_market_index_uses_usda_then_trend():
    usda = {2025: 1.0, 2026: 0.708, 2027: 0.691}
    assert sc.market_index(2027, usda, 3) == 0.691
    assert sc.market_index(2029, usda, -3) == pytest.approx(0.691 * 0.97 ** 2)


def test_volume_and_binding_constraint():
    assert sc.volume(0, 3000) == (0, "none")
    assert sc.volume(2000, 3000) == (2000, "capacity")
    assert sc.volume(5000, 3000) == (3000, "market")


def test_nan_is_zero():
    assert sc.num(float("nan")) == 0 and sc.num(None) == 0 and sc.num(4.9) == 4.9
    assert (float("nan") or 0) != (float("nan") or 0)        # por qué hace falta: NaN or 0 sigue siendo NaN


def test_rate_at_reads_an_scd2_schedule():
    sch = pd.DataFrame([dict(valid_from=date(2024, 5, 1), valid_to=date(2024, 12, 31), rate_pct=11.2),
                        dict(valid_from=date(2025, 1, 1), valid_to=date(2262, 4, 11), rate_pct=10.4)])
    assert sc.rate_at(sch, date(2024, 7, 1)) == 11.2 and sc.rate_at(sch, date(2030, 7, 1)) == 10.4
    assert sc.rate_at(sch, date(2020, 1, 1)) is None


@pytest.fixture(scope="module")
def conn():
    with get_engine("etl").connect() as c:
        if not c.execute(text("SELECT COUNT(*) FROM pork_gold.fact_scenario_market")).scalar():
            pytest.skip("escenarios vacíos: corre primero .\\\\pipeline.ps1")
        yield c


def test_every_scenario_has_ten_years(conn):
    rows = conn.execute(text("""SELECT COUNT(DISTINCT scenario_key), COUNT(*), MIN(year_n), MAX(year_n)
                                FROM pork_gold.fact_scenario_market""")).one()
    assert tuple(rows) == (24, 240, 1, 10)


def test_volume_never_exceeds_capacity_nor_market(conn):
    bad = conn.execute(text("""SELECT COUNT(*) FROM pork_gold.fact_scenario_market
                               WHERE agroporc_t > capacity_t + 0.1 OR agroporc_t > som_cap_t + 0.1""")).scalar()
    assert bad == 0


def test_no_certification_means_no_sales(conn):
    t = conn.execute(text("""SELECT SUM(m.agroporc_t) FROM pork_gold.fact_scenario_market m
                             JOIN pork_gold.dim_scenario s ON s.scenario_key = m.scenario_key
                             WHERE s.cert_year IS NULL""")).scalar()
    assert float(t) == 0


def test_case_c_sells_more_than_a(conn):
    tot = dict(conn.execute(text("""SELECT s.trade_case, SUM(m.agroporc_t) FROM pork_gold.fact_scenario_market m
                                    JOIN pork_gold.dim_scenario s ON s.scenario_key = m.scenario_key
                                    GROUP BY s.trade_case""")).all())
    assert tot["C"] > tot["B"] > tot["A"]


def test_lifting_retaliation_makes_usa_cheaper(conn):
    v = dict(conn.execute(text("""
        SELECT s.trade_case, l.landed_usd_kg FROM pork_gold.fact_landed_cost l
        JOIN pork_gold.dim_scenario s ON s.scenario_key = l.scenario_key AND s.code IN ('A-up-2','B-up-2','C-up-2')
        JOIN pork_gold.dim_country c ON c.country_key = l.supplier_key AND c.iso3 = 'USA'
        JOIN pork_gold.dim_product p ON p.product_key = l.product_key AND p.hs_code = '020649'""")).all())
    assert v["A"] < v["B"] < v["C"]
