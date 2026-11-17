"""
test_monte_carlo.py · Fase 14.3 · el motor vectorizado reproduce finance.cashflow y los resultados guardados son coherentes.
"""
import numpy as np
import pytest
from sqlalchemy import text

from src import finance as fi
from src import monte_carlo as mc
from src.db import get_engine

BASE = {"offal_local_value_usd_kg": 1.0, "ecuador_fob_usd_kg_offal": 1.6, "agroporc_capacity_t": 5000,
        "processing_cost_usd_kg": 0.15, "freezing_cost_usd_kg": 0.05, "export_logistics_usd_kg": 0.05,
        "fixed_cost_usd_year": 100000, "working_capital_months": 2, "capex_blast_freezer": 70000,
        "capex_cold_storage": 135000, "capex_plant_upgrade": 250000, "capex_china_registration": 100000,
        "depreciation_years": 10, "effective_tax_pct": 36.25, "discount_rate": 12}


def test_vectorized_npv_matches_finance_cashflow():
    ramps = np.array([0, 0, 0.4, 0.7, 1, 1, 1, 1, 1, 1])
    caps = np.array([9e3, 9e3, 9e3, 3e3, 9e3, 9e3, 4e3, 9e3, 9e3, 9e3])
    tonnes = [min(BASE["agroporc_capacity_t"] * r, c) if r > 0 else 0.0 for r, c in zip(ramps, caps)]
    expected = fi.cashflow(tonnes, BASE)["discounted_cf"].sum()
    got = mc.npv_vectorized(BASE, ramps, caps)[0]
    assert abs(got - expected) < 1e-6
    # Vectorizado: dos juegos a la vez dan lo mismo que uno por uno
    two = mc.npv_vectorized(BASE | {"offal_local_value_usd_kg": np.array([1.0, 2.0])}, ramps, caps)
    assert abs(two[0] - expected) < 1e-6 and two[1] < two[0]


def test_triangular_respects_range_and_mode():
    rng = np.random.default_rng(1)
    x = mc.triangular(rng, 1.14, 1.38, 2.20, 50_000)
    assert x.min() >= 1.14 and x.max() <= 2.20
    assert abs(x.mean() - (1.14 + 1.38 + 2.20) / 3) < 0.01
    assert (mc.triangular(rng, 10, 10, 10, 5) == 10).all()          # sin rango: valor fijo


@pytest.fixture(scope="module")
def bi():
    with get_engine("bi").connect() as c:
        if not c.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='pork_gold' "
                              "AND table_name='fact_mc_summary'")).scalar():
            pytest.skip("migración 021 no aplicada: corre .\\pipeline.ps1")
        yield c


def test_base_npv_matches_the_pipeline(bi):
    """Con todos los supuestos en base, el Monte Carlo reproduce el VAN de finance.py en los 24 escenarios."""
    rows = bi.execute(text("""SELECT m.npv_base, r.npv_usd FROM pork_gold.fact_mc_summary m
                              JOIN pork_gold.fact_scenario_result r USING (scenario_key)""")).all()
    assert len(rows) == 24
    assert max(abs(a - float(b)) for a, b in rows) < 1


def test_summary_is_coherent(bi):
    rows = bi.execute(text("""SELECT m.p_npv_pos, m.npv_p05, m.npv_p50, m.npv_p95, s.cert_year
                              FROM pork_gold.fact_mc_summary m JOIN pork_gold.dim_scenario s USING (scenario_key)""")).all()
    for p, p5, p50, p95, cert in rows:
        assert 0 <= p <= 1 and p5 <= p50 <= p95
        if cert is None:
            assert p == 0                                            # sin certificación nunca se gana
    hist = bi.execute(text("SELECT scenario_key, SUM(n) FROM pork_gold.fact_mc_hist GROUP BY scenario_key")).all()
    n = bi.execute(text("SELECT MAX(n_draws) FROM pork_gold.fact_mc_summary")).scalar()
    assert all(int(s) == n for _, s in hist)


def test_tornado_has_every_uncertain_assumption(bi):
    k = bi.execute(text("SELECT scenario_key FROM pork_gold.fact_mc_summary LIMIT 1")).scalar()
    got = set(bi.execute(text("SELECT assumption FROM pork_gold.fact_mc_tornado WHERE scenario_key = :k"),
                         {"k": k}).scalars())
    assert got == set(mc.UNCERTAIN)
