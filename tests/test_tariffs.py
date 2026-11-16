"""
test_tariffs.py · Migración 004: NMF de China por línea HS, tasa provisional 2020-2021,
desgravación (supuesto) del acuerdo Ecuador–China y producción de Ecuador.
"""
import pytest
from sqlalchemy import text

from src.db import SILVER, get_engine


def rate(conn, hs, on, target="NULL", mtype="mfn"):
    """Tasa vigente en una fecha (NULL = NMF para todos los orígenes)."""
    cond = "m.target_id IS NULL" if target == "NULL" else "t.iso3 = :tgt"
    return conn.execute(text(f"""
        SELECT m.rate_pct FROM {SILVER}.trade_measure m
        LEFT JOIN {SILVER}.country t ON t.country_id = m.target_id
        WHERE m.hs_code = :hs AND m.measure_type = :mt AND {cond}
          AND :d BETWEEN m.valid_from AND m.valid_to"""),
        {"hs": hs, "mt": mtype, "d": on, "tgt": target}).scalar()


@pytest.fixture(scope="module")
def conn():
    with get_engine("etl").connect() as c:
        yield c


@pytest.mark.parametrize("hs,expected", [
    ("020329", 12), ("020649", 12), ("020641", 12),    # congelados
    ("020319", 20), ("020630", 20),                    # frescos o refrigerados
    ("021012", 25),                                    # salados o ahumados
])
def test_mfn_by_line_2026(conn, hs, expected):
    assert float(rate(conn, hs, "2026-06-01")) == expected


def test_provisional_rate_2020_2021_is_scd2(conn):
    assert [float(rate(conn, "020329", d)) for d in ("2019-06-01", "2020-06-01", "2021-12-31", "2022-01-01")] \
        == [12, 8, 8, 12]
    assert float(rate(conn, "020649", "2020-06-01")) == 12      # las vísceras no tuvieron rebaja


def test_ecuador_preferential_schedule(conn):
    assert float(rate(conn, "020649", "2025-03-01", "ECU", "preferential")) == pytest.approx(10.4)
    assert float(rate(conn, "020630", "2024-06-01", "ECU", "preferential")) == pytest.approx(18.67)
    assert float(rate(conn, "020649", "2040-01-01", "ECU", "preferential")) == 0
    assert rate(conn, "021012", "2025-03-01", "ECU", "preferential") is None   # procesados: sin supuesto


def test_ecuador_production_loaded(conn):
    rows = conn.execute(text(f"""
        SELECT p.year, s.name, p.production_t, p.is_estimate FROM {SILVER}.country_production p
        JOIN {SILVER}.country c ON c.country_id = p.country_id AND c.iso3 = 'ECU'
        JOIN {SILVER}.source s ON s.source_id = p.source_id ORDER BY p.year, s.name""")).all()
    assert (2023, "aspe", 213000, 0) in [(r[0], r[1], int(r[2]), int(r[3])) for r in rows]
    assert any(r[0] == 2024 and r[3] for r in rows)             # 2024 marcado como estimado
