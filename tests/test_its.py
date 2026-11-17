"""
test_its.py · Fase 14.2 · serie de tiempo interrumpida, protección del modelo (gold desde 2018) y sección 301.
"""
import numpy as np
import pandas as pd
import pytest
from sqlalchemy import text

from src import its
from src.db import get_engine


def test_newey_west_recovers_known_coefficients():
    """Con datos simulados de un corte conocido, el modelo recupera el salto y la pendiente."""
    rng = np.random.default_rng(7)
    idx = pd.date_range("2015-01-01", "2026-06-01", freq="MS")
    X = its.design(idx)
    truth = pd.Series(0.0, index=X.columns)
    truth[["const", "trend", "level_2018", "slope_2018", "level_2020"]] = [15, 0.1, -10, 0.05, 8]
    y = X @ truth + rng.normal(0, 0.5, len(idx))
    f = its.fit("sim", pd.Series(y.values, index=idx))
    est = f.coef.set_index("term")["estimate"]
    assert abs(est["level_2018"] + 10) < 1 and abs(est["level_2020"] - 8) < 1 and abs(est["trend"] - 0.1) < 0.05
    c = f.coef.set_index("term")
    for term, true in (("level_2018", -10), ("level_2020", 8)):
        assert abs(c.loc[term, "estimate"] - true) < 3 * c.loc[term, "se"]   # dentro de 3 errores estándar


def test_design_has_seasonality_and_two_cuts():
    idx = pd.date_range("2015-01-01", "2021-12-01", freq="MS")
    X = its.design(idx)
    assert [c for c in X.columns if c.startswith("m")] == [f"m{m:02d}" for m in range(2, 13)]
    assert X.loc["2018-03-01", "level_2018"] == 0 and X.loc["2018-04-01", "level_2018"] == 1
    assert X.loc["2018-06-01", "slope_2018"] == 2 and X.loc["2020-02-01", "level_2020"] == 1


def test_gap_months_are_missing():
    idx = pd.date_range("2019-11-01", "2020-04-01", freq="MS")
    m = pd.DataFrame({"us_value": 1.0, "rest_value": 4.0, "us_t": 1.0, "rest_t": 4.0}, index=idx)
    ys = its.outcomes(m)
    assert ys["share_value"][its.GAP].isna().all() and ys["share_value"].notna().sum() == 4


@pytest.fixture(scope="module")
def bi():
    with get_engine("bi").connect() as c:
        if not c.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='pork_gold' "
                              "AND table_name='fact_its_coef'")).scalar():
            pytest.skip("migración 020 no aplicada: corre .\\pipeline.ps1")
        yield c


def test_its_results_are_stored_for_three_models(bi):
    rows = dict(bi.execute(text("SELECT model, MIN(n_obs) FROM pork_gold.fact_its_coef GROUP BY model")).all())
    assert set(rows) == {"share_value", "share_tonnes", "log_us_value"}
    assert rows["share_value"] >= 100                     # 2015 en adelante, sin ene-feb 2020
    gap = bi.execute(text("SELECT COUNT(*) FROM pork_gold.fact_its_series WHERE is_gap = 1 "
                          "AND observed IS NOT NULL")).scalar()
    assert gap == 0


def test_gold_still_starts_in_2018(bi):
    """2015-2017 están en silver solo para la ITS: el modelo (gold) sigue empezando en 2018."""
    first = bi.execute(text("SELECT MIN(date_key) FROM pork_gold.fact_china_imports")).scalar()
    assert first >= 20180101


def test_section_301_in_us_tariff(bi):
    """Supuesto #47: 62% entre jul-2018 y feb-2020; desde mar-2020 se supone la exclusión de la 301 (37%)."""
    q = text("""SELECT t.total_max_pct FROM pork_gold.fact_tariff_applied t
                JOIN pork_gold.dim_country c ON c.country_key = t.origin_key AND c.iso3 = 'USA'
                JOIN pork_gold.dim_product p ON p.product_key = t.product_key AND p.hs_code = '020649'
                WHERE t.date_key = :d""")
    assert float(bi.execute(q, {"d": 20180801}).scalar()) == 62
    assert float(bi.execute(q, {"d": 20200601}).scalar()) == 37
