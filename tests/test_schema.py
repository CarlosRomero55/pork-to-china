"""
test_schema.py · Prueba que las reglas de la base RECHAZAN datos malos.

Cada prueba intenta insertar algo inválido dentro de una transacción y
verifica que MySQL lo bloquee. Al final se hace ROLLBACK: no deja basura.
Uso:  python -m pytest tests/test_schema.py -v   (requiere .env con pork_etl)
"""
import pymysql
import pytest

from src.config import settings

S = settings.db_silver


@pytest.fixture()
def cur():
    conn = pymysql.connect(host=settings.db_host, port=settings.db_port, user=settings.db_user,
                           password=settings.db_password, charset="utf8mb4", autocommit=False)
    c = conn.cursor()
    yield c
    conn.rollback()
    conn.close()


def test_trade_measure_duplicate_version_rejected(cur):
    """La misma medida, para el mismo destino y la misma fecha de inicio, no puede repetirse."""
    cur.execute(f"""SELECT imposing_id, target_id, target_group_id, target_company, hs_code,
                           measure_type, rate_pct, valid_from, valid_to, source_id
                    FROM {S}.trade_measure WHERE measure_type='mfn' LIMIT 1""")
    row = cur.fetchone()
    with pytest.raises(pymysql.err.IntegrityError):
        cur.execute(f"""INSERT INTO {S}.trade_measure
            (imposing_id, target_id, target_group_id, target_company, hs_code,
             measure_type, rate_pct, valid_from, valid_to, source_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", row)


def test_measure_dates_check(cur):
    """valid_to no puede ser anterior a valid_from."""
    with pytest.raises(pymysql.err.OperationalError):  # MySQL reporta CHECK como error 3819
        cur.execute(f"""INSERT INTO {S}.trade_measure
            (imposing_id, hs_code, measure_type, rate_pct, valid_from, valid_to, source_id)
            SELECT country_id, '020649', 'mfn', 5, '2026-01-01', '2025-01-01', 1
            FROM {S}.country WHERE iso3='CHN'""")


def test_trade_flow_period_must_be_day_1(cur):
    """El periodo mensual se guarda siempre como el día 1."""
    with pytest.raises(pymysql.err.OperationalError):
        cur.execute(f"""INSERT INTO {S}.trade_flow
            (reporter_id, partner_id, hs_code, period, flow_type, net_weight_kg, value_usd, source_id, batch_id)
            SELECT c.country_id, p.country_id, '020649', '2025-03-15', 'M', 1, 1, 1, 0
            FROM {S}.country c, {S}.country p WHERE c.iso3='CHN' AND p.iso3='USA'""")


def test_trade_flow_unknown_hs_rejected(cur):
    """No se puede cargar comercio de una línea HS que no está en el catálogo."""
    with pytest.raises(pymysql.err.IntegrityError):
        cur.execute(f"""INSERT INTO {S}.trade_flow
            (reporter_id, partner_id, hs_code, period, flow_type, net_weight_kg, value_usd, source_id, batch_id)
            SELECT c.country_id, p.country_id, '999999', '2025-03-01', 'M', 1, 1, 1, 0
            FROM {S}.country c, {S}.country p WHERE c.iso3='CHN' AND p.iso3='USA'""")


def test_assumption_range_check(cur):
    """En un supuesto, mín <= base <= máx."""
    with pytest.raises(pymysql.err.OperationalError):
        cur.execute(f"""INSERT INTO {S}.assumption (name, version, value_min, value_base, value_max, unit)
                        VALUES ('test_bad_range', 1, 10, 5, 20, '%')""")


def test_uk_left_eu_on_2020_01_31(cur):
    """La pertenencia temporal a la UE refleja el Brexit."""
    cur.execute(f"""SELECT COUNT(*) FROM {S}.country_group_member m
                    JOIN {S}.country c ON c.country_id = m.country_id
                    WHERE c.iso3='GBR' AND '2025-06-01' BETWEEN m.valid_from AND m.valid_to""")
    assert cur.fetchone()[0] == 0
    cur.execute(f"""SELECT COUNT(*) FROM {S}.country_group_member m
                    JOIN {S}.country c ON c.country_id = m.country_id
                    WHERE '2025-06-01' BETWEEN m.valid_from AND m.valid_to""")
    assert cur.fetchone()[0] == 27
