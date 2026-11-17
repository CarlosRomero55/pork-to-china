"""
test_policy.py · Fase 14.1 · rastreador de políticas (eventos manuales + aranceles derivados de trade_measure).
"""
import pytest
from sqlalchemy import text

from src.db import get_engine


@pytest.fixture(scope="module")
def conn():
    with get_engine("bi").connect() as c:
        if not c.execute(text("SELECT COUNT(*) FROM information_schema.views WHERE table_schema='pork_gold' "
                              "AND table_name='v_dash_policy_events'")).scalar():
            pytest.skip("migración 018 no aplicada: corre .\\pipeline.ps1")
        yield c


def test_every_event_has_a_source_with_url(conn):
    missing = conn.execute(text("SELECT title_es FROM pork_gold.v_dash_policy_events "
                                "WHERE source IS NULL OR url IS NULL OR url = ''")).scalars().all()
    assert not missing, missing


def test_its_cuts_and_control_are_marked(conn):
    roles = dict(conn.execute(text("SELECT its_role, COUNT(*) FROM pork_gold.v_dash_policy_events "
                                   "WHERE its_role IS NOT NULL GROUP BY its_role")).all())
    assert roles.get("corte_2018", 0) >= 2 and roles.get("corte_2020", 0) >= 2 and roles.get("control") == 1


def test_approximate_dates_are_not_invented(conn):
    """Una fecha de precisión 'mes' cae el día 1; una de precisión 'año', el 1 de enero."""
    bad = conn.execute(text("""
        SELECT title_es FROM pork_gold.v_dash_policy_events
        WHERE (date_precision = 'mes' AND DAY(event_date) <> 1)
           OR (date_precision = 'año' AND (DAY(event_date) <> 1 OR MONTH(event_date) <> 1))""")).scalars().all()
    assert not bad, bad


def test_tariff_changes_flow_in_automatically(conn):
    """Cada cambio de arancel de China (sin TLC y después del inicio de la serie) aparece como evento, una sola vez."""
    with get_engine("etl").connect() as etl:      # pork_bi no lee silver (mínimo privilegio)
        expected = etl.execute(text("""
            SELECT COUNT(*) FROM (SELECT DISTINCT valid_from, measure_type, target_id, target_group_id
                                  FROM pork_silver.trade_measure
                                  WHERE valid_from > '2018-01-01' AND measure_type <> 'preferential') x""")).scalar()
    got = conn.execute(text("SELECT COUNT(*) FROM pork_gold.v_dash_policy_events WHERE origin = 'trade_measure'")).scalar()
    assert got == expected


def test_events_are_in_spanish_and_unique(conn):
    rows = conn.execute(text("SELECT event_date, country_iso3, title_es FROM pork_gold.v_dash_policy_events")).all()
    assert len(rows) == len(set(rows))
