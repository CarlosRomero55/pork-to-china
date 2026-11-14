"""
test_db.py · Pruebas de la capa de acceso a datos (src/db.py).
Las pruebas de datos corren dentro de una transacción que se revierte.
Uso:  python -m pytest tests/test_db.py -v
"""
from datetime import date

import pandas as pd
import pytest
from sqlalchemy import text

from src.db import BRONZE, SILVER, get_engine, payload_hash, save_raw_response, track_batch, upsert_df

UPDATE_COLS = ["net_weight_kg", "value_usd", "batch_id"]


@pytest.fixture()
def conn():
    with get_engine("etl").connect() as c:
        trans = c.begin()
        yield c
        trans.rollback()


def _flows(conn, batch_id):
    ids = dict(conn.execute(text(f"SELECT iso3, country_id FROM {SILVER}.country "
                                  "WHERE iso3 IN ('CHN','USA','ESP')")).all())
    src = conn.execute(text(f"SELECT source_id FROM {SILVER}.source WHERE name='comtrade'")).scalar()
    return pd.DataFrame({
        "reporter_id": [ids["CHN"]] * 2, "partner_id": [ids["USA"], ids["ESP"]],
        "hs_code": ["020649"] * 2, "period": [date(2025, 3, 1)] * 2, "flow_type": ["M"] * 2,
        "net_weight_kg": [1000.0, float("nan")], "value_usd": [2150.0, 3000.0],
        "source_id": [src] * 2, "batch_id": [batch_id] * 2,
    })


def _batch(conn):
    return conn.execute(text(f"INSERT INTO {BRONZE}.extract_batch (source_name) VALUES ('pytest')")).lastrowid


def test_hash_ignores_key_order():
    assert payload_hash({"a": 1, "b": [1, 2]}) == payload_hash({"b": [1, 2], "a": 1})
    assert payload_hash({"a": 1}) != payload_hash({"a": 2})


def test_raw_response_not_duplicated(conn):
    b = _batch(conn)
    _, first = save_raw_response(conn, b, "pytest", "/x", {}, {"k": [1, 2, 3]})
    _, second = save_raw_response(conn, b, "pytest", "/x", {}, {"k": [1, 2, 3]})
    assert first is True and second is False


def test_upsert_is_idempotent(conn):
    df = _flows(conn, _batch(conn))
    r1 = upsert_df(conn, df, SILVER, "trade_flow", UPDATE_COLS)
    r2 = upsert_df(conn, df, SILVER, "trade_flow", UPDATE_COLS)
    assert (r1.inserted, r1.updated) == (2, 0)
    assert (r2.inserted, r2.updated, r2.unchanged) == (0, 0, 2)


def test_upsert_applies_corrections(conn):
    df = _flows(conn, _batch(conn))
    upsert_df(conn, df, SILVER, "trade_flow", UPDATE_COLS)
    df.loc[0, "value_usd"] = 2200.0
    r = upsert_df(conn, df, SILVER, "trade_flow", UPDATE_COLS)
    assert (r.inserted, r.updated, r.unchanged) == (0, 1, 1)


def test_nan_becomes_null(conn):
    df = _flows(conn, _batch(conn))
    upsert_df(conn, df, SILVER, "trade_flow", UPDATE_COLS)
    n_null = conn.execute(text(f"SELECT COUNT(*) FROM {SILVER}.trade_flow "
                               "WHERE value_usd = 3000 AND net_weight_kg IS NULL")).scalar()
    assert n_null == 1


def test_unknown_column_rejected(conn):
    df = _flows(conn, _batch(conn)).assign(columna_inventada=1)
    with pytest.raises(ValueError):
        upsert_df(conn, df, SILVER, "trade_flow", UPDATE_COLS)


def test_failed_batch_is_recorded():
    """Si la extracción falla, el lote queda como 'failed' con el mensaje de error."""
    eng = get_engine("etl")
    with pytest.raises(RuntimeError):
        with track_batch("pytest_fail", {"demo": True}) as b:
            batch_id = b.batch_id
            raise RuntimeError("API caída (simulado)")
    with eng.begin() as c:
        status, msg = c.execute(text(f"SELECT status, error_msg FROM {BRONZE}.extract_batch "
                                     "WHERE batch_id=:b"), {"b": batch_id}).one()
        c.execute(text(f"DELETE FROM {BRONZE}.extract_batch WHERE source_name LIKE 'pytest%'"))
    assert status == "failed" and "API caída" in msg
