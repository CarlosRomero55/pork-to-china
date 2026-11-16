"""
test_finance.py · Fase 10.3 · flujo de caja, VAN, TIR y puntos de equilibrio.
Las fórmulas se prueban con un caso pequeño hecho a mano; luego, reglas sobre lo que quedó en gold.
"""
import numpy as np
import pytest
from sqlalchemy import text

from src import finance as fi
from src.db import get_engine

# Proyecto de juguete: inversión 1.000 USD, margen 0,50 USD/kg, sin costo fijo, sin impuesto ni capital de trabajo
TOY = dict(capex_blast_freezer=1000, capex_cold_storage=0, capex_plant_upgrade=0, capex_china_registration=0,
           offal_local_value_usd_kg=1.0, processing_cost_usd_kg=0, freezing_cost_usd_kg=0, export_logistics_usd_kg=0,
           ecuador_fob_usd_kg_offal=1.5, fixed_cost_usd_year=0, effective_tax_pct=0, depreciation_years=10,
           working_capital_months=0, discount_rate=10, jobs_fixed=5, jobs_per_1000t=2,
           entry_ramp_y1_pct=40, entry_ramp_y2_pct=70)


def test_cashflow_by_hand():
    cf = fi.cashflow([1.0, 1.0], TOY)        # 1 t/año = 1.000 kg × 0,50 = 500 USD por año
    assert cf["net_cashflow"].tolist() == [-1000, 500, 500]
    assert cf["discounted_cf"].sum() == pytest.approx(-1000 + 500 / 1.1 + 500 / 1.21)


def test_tax_only_on_positive_profit_after_depreciation():
    p = TOY | {"effective_tax_pct": 50, "depreciation_years": 2}
    cf = fi.cashflow([1.0, 0.0], p)          # dep = 1.000 / 2 = 500 · año 1: 500 − 500 = 0 → 0 · año 2: pérdida → 0
    assert cf["tax"].tolist() == [0, 0, 0]
    cf10 = fi.cashflow([1.0, 0.0], TOY | {"effective_tax_pct": 50})   # dep 100 · año 1: (500 − 100) × 50% = 200
    assert cf10["tax"].tolist() == [0, 200, 0]


def test_working_capital_is_recovered_at_the_end():
    p = TOY | {"working_capital_months": 12}
    cf = fi.cashflow([1.0, 1.0, 1.0], p)
    assert cf["net_cashflow"].sum() == pytest.approx(fi.cashflow([1.0, 1.0, 1.0], TOY)["net_cashflow"].sum())


def test_payback_interpolates_and_irr_needs_a_sign_change():
    assert fi.payback(np.array([-1000, 500, 500])) == 2.0
    assert fi.payback(np.array([-1000, 400, 400, 400])) == pytest.approx(2.5)
    assert fi.payback(np.array([-1000, 100])) is None
    assert fi.irr(np.array([-1000.0, 0, 0])) is None
    assert fi.irr(np.array([-1000.0, 1100])) == pytest.approx(10.0)


def test_breakeven_offal_value_gives_zero_npv():
    res, _ = fi.evaluate([1.0] * 10, TOY, cert_year=1)
    v = res["breakeven_offal_usd_kg"]
    npv = fi.cashflow([1.0] * 10, TOY | {"offal_local_value_usd_kg": v})["discounted_cf"].sum()
    # El resultado se guarda con 3 decimales (0,001 USD/kg): con 10.000 kg en 10 años, ±0,0005 USD/kg mueve
    # el VAN hasta ~3 USD. Por eso la tolerancia es 5 USD y no 1.
    assert abs(npv) < 5 and v > TOY["offal_local_value_usd_kg"]          # el proyecto de juguete gana


def test_never_certified_loses_the_investment():
    res, _ = fi.evaluate([0.0] * 10, TOY, cert_year=None)
    assert res["npv_usd"] == -1000 and res["irr_pct"] is None and res["breakeven_offal_usd_kg"] is None
    assert res["jobs"] == 0


@pytest.fixture(scope="module")
def conn():
    with get_engine("etl").connect() as c:
        if not c.execute(text("SELECT COUNT(*) FROM pork_gold.fact_scenario_result")).scalar():
            pytest.skip("resultados vacíos: corre primero .\\\\pipeline.ps1")
        yield c


def test_results_and_cashflows_are_complete(conn):
    assert conn.execute(text("SELECT COUNT(*) FROM pork_gold.fact_scenario_result")).scalar() == 24
    assert conn.execute(text("SELECT COUNT(*) FROM pork_gold.fact_scenario_cashflow")).scalar() == 24 * 11


def test_npv_equals_sum_of_discounted_flows(conn):
    bad = conn.execute(text("""
        SELECT COUNT(*) FROM pork_gold.fact_scenario_result r
        JOIN (SELECT scenario_key, SUM(discounted_cf) s FROM pork_gold.fact_scenario_cashflow GROUP BY scenario_key) c
          ON c.scenario_key = r.scenario_key
        WHERE ABS(r.npv_usd - c.s) > 5""")).scalar()
    assert bad == 0


def test_earlier_certification_tolerates_a_higher_local_value(conn):
    """Certificar antes deja más años de exportación: el valor local máximo que aguanta el proyecto sube.
    (No depende del valor base de la víscera, a diferencia del VAN, que puede ser negativo en todos.)"""
    rows = conn.execute(text("""
        SELECT s.trade_case, s.china_selfsuff, s.cert_year, r.breakeven_offal_usd_kg FROM pork_gold.fact_scenario_result r
        JOIN pork_gold.dim_scenario s ON s.scenario_key = r.scenario_key WHERE s.cert_year IS NOT NULL""")).all()
    by = {}
    for tc, cs, cy, be in rows:
        by.setdefault((tc, cs), {})[cy] = float(be)
    for v in by.values():
        assert v[2] > v[4] > v[6]


def test_npv_sign_matches_offal_breakeven_vs_base(conn):
    """VAN > 0 si y solo si el valor local base de la víscera está por debajo del máximo que tolera el escenario."""
    base = conn.execute(text("""
        SELECT a.value_base FROM pork_silver.assumption a
        WHERE a.name = 'offal_local_value_usd_kg' ORDER BY a.version DESC LIMIT 1""")).scalar()
    rows = conn.execute(text("""
        SELECT npv_usd, breakeven_offal_usd_kg FROM pork_gold.fact_scenario_result
        WHERE breakeven_offal_usd_kg IS NOT NULL""")).all()
    assert rows
    for npv, be in rows:
        assert (float(npv) > 0) == (float(be) > float(base))


def test_scenarios_use_the_sourced_offal_value(conn):
    """Migración 015: los 24 escenarios usan la v2 del valor local de la víscera (con referencias), no la v1."""
    versions = conn.execute(text("""
        SELECT DISTINCT a.version FROM pork_silver.scenario_assumption sa
        JOIN pork_silver.assumption a ON a.assumption_id = sa.assumption_id
        WHERE a.name = 'offal_local_value_usd_kg'""")).scalars().all()
    assert versions == [2]
    src = conn.execute(text("""
        SELECT a.source_id FROM pork_silver.assumption a
        WHERE a.name = 'offal_local_value_usd_kg' AND a.version = 2""")).scalar()
    assert src is not None
