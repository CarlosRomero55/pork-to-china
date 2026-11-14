"""
test_extract_comtrade.py · Pruebas del extractor de Comtrade SIN llamar a la API real.
Se usa una sesión HTTP falsa que devuelve respuestas simuladas con la forma real de Comtrade.
Uso:  python -m pytest tests/test_extract_comtrade.py -v
"""
import dataclasses

import pytest
from sqlalchemy import text

import src.extract_comtrade as ec
from src.db import BRONZE, get_engine


def fake_payload(query, value=100.0):
    """Respuesta con la estructura de Comtrade: 2 socios × 1 línea HS × 12 meses (+ Mundo)."""
    data = []
    for m in range(1, 13):
        for partner, factor in ((0, 3), (842, 1), (724, 2)):   # Mundo, EE. UU., España
            data.append({"period": f"{query.year}{m:02d}", "reporterCode": query.reporter_code,
                         "partnerCode": partner, "cmdCode": "020649", "flowCode": query.flow,
                         "netWgt": 1000.0 * factor, "primaryValue": value * factor})
    return {"elapsedTime": "0.1 secs", "count": len(data), "data": data, "error": ""}


class FakeResponse:
    def __init__(self, status, payload=None, headers=None):
        self.status_code, self._payload, self.headers = status, payload, headers or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    """Devuelve las respuestas en orden; registra cada llamada."""
    def __init__(self, script=None, value=100.0):
        self.calls, self.script, self.value = [], list(script or []), value

    def get(self, url, params, timeout, headers):
        year = int(params["period"][:4])
        q = ec.Query(int(params["reporterCode"]), "X", params["flowCode"], year)
        self.calls.append((params["reporterCode"], params["flowCode"], year))
        if self.script:
            status = self.script.pop(0)
            if status != 200:
                return FakeResponse(status, headers={"Retry-After": "0"})
        return FakeResponse(200, fake_payload(q, self.value))


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """Caché en carpeta temporal, sin pausas ni esperas, llave falsa; limpia bronze al final."""
    monkeypatch.setattr(ec, "CACHE_DIR", tmp_path / "comtrade")
    monkeypatch.setattr(ec.time, "sleep", lambda s: None)
    monkeypatch.setattr(ec.fetch.retry, "sleep", lambda s: None)
    monkeypatch.setattr(ec, "settings", dataclasses.replace(ec.settings, comtrade_api_key="test-key"))
    yield
    with get_engine("etl").begin() as c:
        c.execute(text(f"DELETE FROM {BRONZE}.raw_api_response WHERE batch_id IN "
                       f"(SELECT batch_id FROM {BRONZE}.extract_batch WHERE params->>'$.start_year' = '1990')"))
        c.execute(text(f"DELETE FROM {BRONZE}.extract_batch WHERE params->>'$.start_year' = '1990'"))


def test_plan_counts():
    to_fetch, cached = ec.build_plan(1990, 1992)
    assert len(to_fetch) == 6 and cached == []           # 2 reporters × 3 años, sin caché
    assert to_fetch[0].params()["period"].startswith("199001,199002")
    assert to_fetch[0].params()["partner2Code"] == 0     # solo totales


def test_extract_saves_to_bronze_and_cache():
    s = FakeSession()
    stats = ec.run(1990, 1990, session=s, pause=0)
    assert stats["fetched"] == 2 and stats["new_raw"] == 2 and stats["records"] == 72
    assert (ec.CACHE_DIR / "CHN_M_1990.json").exists()
    assert (ec.CACHE_DIR / "ECU_X_1990.json").exists()


def test_rerun_does_not_duplicate_bronze():
    ec.run(1990, 1990, session=FakeSession(), pause=0)
    stats = ec.run(1990, 1990, session=FakeSession(), pause=0)   # misma data → mismo hash
    assert stats["new_raw"] == 0


def test_closed_years_come_from_cache():
    ec.run(1990, 1994, session=FakeSession(), pause=0)             # llena la caché
    s = FakeSession()
    stats = ec.run(1990, 1994, session=s, pause=0)
    # cerrados = 1990–1992 (fuera de la ventana de 2 años) → solo 1993 y 1994 van a la API
    assert stats["cached"] == 6 and stats["fetched"] == 4
    assert sorted({c[2] for c in s.calls}) == [1993, 1994]


def test_revised_data_enters_as_new_version():
    ec.run(1990, 1990, session=FakeSession(value=100.0), pause=0)
    stats = ec.run(1990, 1990, session=FakeSession(value=101.0), pause=0)   # la fuente corrige
    assert stats["new_raw"] == 2       # bronze guarda ambas versiones (inmutable)


def test_retries_on_429_then_succeeds():
    s = FakeSession(script=[429, 503, 200, 200])
    stats = ec.run(1990, 1990, session=s, pause=0)
    assert stats["fetched"] == 2 and len(s.calls) == 4


def test_invalid_key_fails_fast_and_batch_is_failed():
    class Denied(FakeSession):
        def get(self, *a, **k):
            self.calls.append(1)
            return FakeResponse(401)
    s = Denied()
    with pytest.raises(PermissionError):
        ec.run(1990, 1990, session=s, pause=0)
    assert len(s.calls) == 1           # 401 no se reintenta
    with get_engine("etl").connect() as c:
        status = c.execute(text(f"SELECT status FROM {BRONZE}.extract_batch "
                                "WHERE params->>'$.start_year'='1990' ORDER BY batch_id DESC LIMIT 1")).scalar()
    assert status == "failed"


def test_api_error_field_raises():
    class ErrSession(FakeSession):
        def get(self, *a, **k):
            return FakeResponse(200, {"data": [], "error": "Invalid parameter"})
    with pytest.raises(RuntimeError, match="Invalid parameter"):
        ec.run(1990, 1990, session=ErrSession(), pause=0)
