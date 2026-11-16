"""
test_benchmark.py · Fase 13.3 · benchmark de acceso sanitario a China y corrección del estado de la PPC.
Se omite si la migración 017 no está aplicada.
"""
import pytest
from sqlalchemy import text

from src.db import get_engine


@pytest.fixture(scope="module")
def conn():
    with get_engine("bi").connect() as c:
        if not c.execute(text("SELECT COUNT(*) FROM information_schema.views WHERE table_schema='pork_gold' "
                              "AND table_name='v_dash_access_benchmark'")).scalar():
            pytest.skip("migración 017 no aplicada: corre .\\pipeline.ps1")
        yield c


def test_benchmark_has_the_three_competitors_and_ecuador(conn):
    rows = {r.iso3: r for r in conn.execute(text("SELECT * FROM pork_gold.v_dash_access_benchmark")).all()}
    assert set(rows) == {"CHL", "CRI", "BRA", "ECU"}
    assert rows["ECU"].first_export is None and rows["ECU"].market_open is None       # sin protocolo
    assert rows["CRI"].years_to_first_export == 7 and rows["BRA"].years_to_first_export == 7
    assert rows["BRA"].regionalized == 1                                               # entró por zonas
    assert all(r.source for r in rows.values())                                        # todo con fuente


def test_competitors_were_csf_free_before_exporting(conn):
    """La lección del benchmark: ninguno exportó a China sin ser libre de PPC (país o zona)."""
    for csf, iso in conn.execute(text("SELECT csf_status_es, iso3 FROM pork_gold.v_dash_access_benchmark "
                                      "WHERE iso3 <> 'ECU'")).all():
        assert "libre" in csf.lower(), iso


def test_sanitary_view_shows_only_the_latest_row_and_mentions_galapagos(conn):
    rows = conn.execute(text("SELECT disease, status_es FROM pork_gold.v_dash_sanitary")).all()
    diseases = [d for d, _ in rows]
    assert len(diseases) == len(set(diseases))                                         # una fila por enfermedad
    ppc = dict(rows)["Peste porcina clásica (PPC)"]
    assert "Galápagos" in ppc
