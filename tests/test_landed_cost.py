"""
test_landed_cost.py · Fase 10.1 · costo puesto en China.
Las fórmulas se prueban con números hechos a mano; al final, una prueba con los datos de gold.
"""
import pandas as pd
import pytest
from sqlalchemy import text

from src import landed_cost as lc
from src.db import get_engine


def test_landed_cost_by_hand():
    # FOB 1,60 + flete 0,20 = 1,80 · seguro 0,5% → CIF 1,809 · arancel 10% → 0,1809 · landed 1,9899
    r = lc.landed_cost(1.60, 0.20, 0.5, 10)
    assert r.cif == pytest.approx(1.809) and r.duty == pytest.approx(0.1809) and r.landed == pytest.approx(1.9899)


def test_zero_tariff_means_landed_equals_cif():
    r = lc.landed_cost(1.35, 0.19, 0.3, 0)
    assert r.landed == pytest.approx(r.cif)


@pytest.mark.parametrize("fob,fr,ins,duty", [(1.6, 0.19, 0.3, 9.6), (2.9, 0.23, 0.5, 47), (1.0, 0.1, 0.2, 0)])
def test_max_fob_is_the_inverse_of_landed(fob, fr, ins, duty):
    target = lc.landed_cost(fob, fr, ins, duty).landed
    assert lc.max_fob_to_match(target, fr, ins, duty) == pytest.approx(fob)


def test_routes():
    assert lc.route_of("ECU") == lc.route_of("CHL") == "pacific"
    assert lc.route_of("BRA") == "brazil" and lc.route_of("ESP") == "europe" and lc.route_of("USA") == "north_america"


@pytest.fixture(scope="module")
def model():
    with get_engine("etl").connect() as conn:
        if not conn.execute(text("SELECT COUNT(*) FROM pork_gold.fact_tariff_applied")).scalar():
            pytest.skip("gold vacío: corre primero .\\\\pipeline.ps1")
        a, market = lc.read_assumptions(conn), lc.read_market(conn)
    return a, market, lc.build(market, a)


def test_latest_assumption_version_is_used(model):
    a, _, _ = model
    with get_engine("etl").connect() as conn:
        latest = conn.execute(text("SELECT MAX(version) FROM pork_silver.assumption "
                                   "WHERE name = 'ecuador_pork_production'")).scalar()
    assert latest >= 2 and a.loc["ecuador_pork_production", "version"] == latest


def test_ecuador_is_price_taker_per_line(model):
    _, _, t = model
    for hs in ("020649", "020329"):
        rows = t[t["hs"] == hs].set_index("proveedor")
        assert rows.loc["Ecuador (con acuerdo)", "fob"] == rows.loc["Chile", "fob"]


def test_agreement_beats_mfn_and_chile_is_cheapest(model):
    _, _, t = model
    v = t[t["hs"] == "020649"].set_index("proveedor")["landed_min"]
    assert v["Ecuador (con acuerdo)"] < v["Ecuador (NMF)"]
    assert v.idxmin() == "Chile"


def test_ranking_is_robust_to_freight(model):
    a, market, _ = model
    s = lc.sensitivity(market, a)
    assert (s["puesto_min"] == s["puesto_base"]).all() and (s["puesto_max"] == s["puesto_base"]).all()
