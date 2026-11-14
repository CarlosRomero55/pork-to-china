"""
test_harmonize.py · bronze → silver con respuestas de Comtrade de prueba.
Todo ocurre dentro de una transacción que se revierte al final.
"""
from datetime import date

import pytest
from sqlalchemy import text

import src.extract_comtrade as ec
from src.db import BRONZE, SILVER, get_engine, save_raw_response
from src.harmonize import build_flows, load, reconciliation
from src.migrate import migrate


def rec(rep, par, flow, wgt, val, hs="020649", period="209901"):
    return {"period": period, "reporterCode": rep, "partnerCode": par, "cmdCode": hs, "flowCode": flow,
            "partner2Code": 0, "customsCode": "C00", "motCode": 0,
            "netWgt": wgt, "primaryValue": val, "isNetWgtEstimated": False}


@pytest.fixture()
def conn():
    with get_engine("etl").connect() as c:
        trans = c.begin()
        b = c.execute(text(f"INSERT INTO {BRONZE}.extract_batch (source_name) VALUES ('pytest')")).lastrowid
        direct = ec.Query("CHN", (156,), "M", None, 2099)
        mirror = ec.Query("MIRROR", (842, 724), "X", 156, 2099)
        # Año ficticio 2099 para no chocar con datos reales
        save_raw_response(c, b, "comtrade", ec.BASE_URL, direct.params(), {"data": [
            rec(156, 842, "M", 1_000_000, 2_100_000), rec(156, 724, "M", 2_000_000, 4_200_000),
            rec(156, 0, "M", 3_000_000, 6_300_000)]})
        save_raw_response(c, b, "comtrade", ec.BASE_URL, mirror.params(), {"data": [
            rec(842, 156, "X", 1_000_000, 2_000_000), rec(724, 156, "X", 2_000_000, 4_000_000)]})
        yield c
        trans.rollback()


def _rows_2099(df):
    return df[df["period"] == date(2099, 1, 1)]


def test_build_separates_direct_and_mirror(conn):
    good, quarantine = build_flows(conn)
    g = _rows_2099(good)
    assert set(g["source"]) == {"comtrade", "comtrade_mirror"}
    assert len(g[g["source"] == "comtrade"]) == 3 and len(g[g["source"] == "comtrade_mirror"]) == 2
    assert len(quarantine) == 0


def test_unknown_country_goes_to_quarantine(conn):
    b = conn.execute(text(f"INSERT INTO {BRONZE}.extract_batch (source_name) VALUES ('pytest')")).lastrowid
    q = ec.Query("CHN", (156,), "M", None, 2098)
    save_raw_response(conn, b, "comtrade", ec.BASE_URL, q.params(),
                      {"data": [rec(156, 999, "M", 10, 10, period="209801")]})
    _, quarantine = build_flows(conn)
    assert (quarantine["partner_code"] == 999).any()


def test_load_is_idempotent(conn):
    good, _ = build_flows(conn)
    g = _rows_2099(good)
    r1, r2 = load(conn, g), load(conn, g)
    assert r1.inserted == 5 and r2.inserted == 0 and r2.updated == 0
    n = conn.execute(text(f"SELECT COUNT(*) FROM {SILVER}.trade_flow WHERE period='2099-01-01'")).scalar()
    assert n == 5


def test_latest_version_wins(conn):
    """Si Comtrade corrige una consulta, silver usa la versión más reciente de bronze."""
    b = conn.execute(text(f"INSERT INTO {BRONZE}.extract_batch (source_name) VALUES ('pytest')")).lastrowid
    direct = ec.Query("CHN", (156,), "M", None, 2099)
    save_raw_response(conn, b, "comtrade", ec.BASE_URL, direct.params(), {"data": [
        rec(156, 842, "M", 1_000_000, 2_500_000), rec(156, 724, "M", 2_000_000, 4_200_000),
        rec(156, 0, "M", 3_000_000, 6_700_000)], "revision": 2})
    good, _ = build_flows(conn)
    usa = good[(good["period"] == date(2099, 1, 1)) & (good["partner_code"] == 842) & (good["source"] == "comtrade")]
    assert len(usa) == 1 and usa["value_usd"].iloc[0] == 2_500_000


def test_reconciliation_ratio(conn):
    good, _ = build_flows(conn)
    g = _rows_2099(good).copy()
    g["period"] = date(2024, 1, 1)          # la conciliación usa 2018–2024
    r = reconciliation(g, {842: "USA", 724: "ESP"})
    assert r.loc["USA", "ratio_valor"] == pytest.approx(1.05)
    assert r.loc["ESP", "ratio_peso"] == pytest.approx(1.0)


def test_migrations_are_idempotent():
    migrate()
    assert migrate() == []
    with get_engine("etl").connect() as c:
        n = c.execute(text(f"""SELECT COUNT(*) FROM {SILVER}.trade_measure m
                               JOIN {SILVER}.country t ON t.country_id = m.target_id
                               WHERE t.iso3 = 'CAN' AND m.measure_type = 'anti_discrimination'
                                 AND '2026-11-13' BETWEEN m.valid_from AND m.valid_to""")).scalar()
    assert n == 9      # 6 líneas de 0203 + 3 de 0206
