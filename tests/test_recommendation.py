"""
test_recommendation.py · Fase 15.1 · la regla de decisión, el semáforo y los umbrales del modelo.
"""
import numpy as np
import pandas as pd
import pytest
from sqlalchemy import text

from src import monte_carlo as mc
from src import recommendation as rec
from src.db import get_engine
from src.scenarios import ramp_share




def frame(d1, d2, d3, d4, d5="en camino"):
    return pd.DataFrame({"role": ["economia", "economia", "acceso", "acceso", "complementario"],
                         "status": [d1, d2, d3, d4, d5]})


def test_decision_rule():
    """Invertir exige UNA condición económica y LAS DOS de acceso; la complementaria no decide."""
    assert rec.decide(frame("cumplido", "no cumplido", "cumplido", "cumplido"))[0] == "revisar la inversión"
    assert rec.decide(frame("no cumplido", "cumplido", "cumplido", "cumplido", "no cumplido"))[0] == "revisar la inversión"
    assert rec.decide(frame("cumplido", "cumplido", "cumplido", "en camino"))[0] == "no invertir hoy"
    assert rec.decide(frame("en camino", "en camino", "cumplido", "cumplido"))[0] == "no invertir hoy"
    why = rec.decide(frame("no cumplido", "no cumplido", "no cumplido", "no cumplido"))[1]
    assert "D1 o D2" in why and "D3 y D4" in why


@pytest.mark.parametrize("current,expected", [(1.10, "cumplido"), (1.18, "en camino"), (1.38, "no cumplido")])
def test_offal_light(current, expected):
    assert rec.numeric_status(current, 1.14, 1.08, 1.19, higher_is_better=False) == expected


@pytest.mark.parametrize("current,expected", [(1.90, "cumplido"), (1.80, "en camino"), (1.47, "no cumplido")])
def test_fob_light(current, expected):
    assert rec.numeric_status(current, 1.84, 1.79, 1.91, higher_is_better=True) == expected


def test_premortem_is_complete():
    assert 6 <= len(rec.PREMORTEM) <= 8
    for r in rec.PREMORTEM:
        assert r["prob"] in ("baja", "media", "alta") and r["impact"] in ("medio", "alto")
        assert r["signal_es"] and "página" in r["watch_es"]


@pytest.fixture(scope="module")
def etl():
    with get_engine("etl").connect() as c:
        if not c.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='pork_gold' "
                              "AND table_name='fact_trigger'")).scalar():
            pytest.skip("migración 022 no aplicada: corre .\\pipeline.ps1")
        yield c


def test_thresholds_give_zero_npv(etl):
    """Con la víscera o el FOB en su umbral, el VAN del escenario de referencia es ~0."""
    th = rec.thresholds(etl).set_index("code")
    assert len(th) == 6 and rec.REFERENCE in th.index
    sc, params, caps, _ = mc.load(etl)
    key = int(sc.loc[sc.code == rec.REFERENCE, "scenario_key"].iloc[0])
    base = params[params.scenario_key == key].set_index("name")["value"].to_dict()
    ramps = np.array([ramp_share(y, 6, base["entry_ramp_y1_pct"], base["entry_ramp_y2_pct"]) for y in range(1, len(caps[key]) + 1)])
    for name, col in (("offal_local_value_usd_kg", "offal_be"), ("ecuador_fob_usd_kg_offal", "fob_be")):
        npv = mc.npv_vectorized(base | {name: th.loc[rec.REFERENCE, col]}, ramps, caps[key])[0]
        assert abs(npv) < 5_000, (name, npv)          # ~0 frente a una inversión de ~0,5 M USD


def test_saved_triggers_are_consistent(etl):
    tr = pd.read_sql(text("SELECT * FROM pork_gold.fact_trigger ORDER BY sort_order"), etl)
    assert list(tr.trigger_code) == ["D1", "D2", "D3", "D4", "D5"]
    num = tr[tr.current_value.notna()]
    assert (num.threshold_min <= num.threshold).all() and (num.threshold <= num.threshold_max).all()
    for r in num.itertuples():
        assert r.status == rec.numeric_status(r.current_value, r.threshold, r.threshold_min, r.threshold_max,
                                              higher_is_better=r.trigger_code == "D2")


def test_bi_reads_triggers():
    """El tablero (pork_bi) lee la tabla de gold."""
    with get_engine("bi").connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM pork_gold.fact_trigger")).scalar() == 5
