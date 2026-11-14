"""
test_extract_comtrade.py · Pruebas del extractor de Comtrade SIN llamar a la API real.
Una sesión HTTP falsa devuelve respuestas con la estructura real de Comtrade.
Uso:  python -m pytest tests/test_extract_comtrade.py -v
"""
import dataclasses

import pytest
from sqlalchemy import text

import src.extract_comtrade as ec
from src.db import BRONZE, get_engine

N_GROUPS = len(ec.QUERY_GROUPS)   # directo China, directo Ecuador, espejo


def fake_data(params, value=100.0):
    """Registros con la forma de Comtrade para los reporters/año pedidos."""
    year = int(params["period"][:4])
    reporters = [int(r) for r in str(params["reporterCode"]).split(",")]
    partners = [int(params["partnerCode"])] if "partnerCode" in params else [0, 842, 724]
    data = []
    for rep in reporters:
        for m in range(1, 13):
            for partner in partners:
                data.append({"period": f"{year}{m:02d}", "reporterCode": rep, "partnerCode": partner,
                             "cmdCode": "020649", "flowCode": params["flowCode"],
                             "netWgt": 1000.0, "primaryValue": value})
    return {"elapsedTime": "0.1 secs", "count": len(data), "data": data, "error": ""}


def fake_da(params):
    """getDa: China publicó hasta 2024-12; Ecuador hasta 2025-06."""
    last = {"156": (2024, 12), "218": (2025, 6)}[str(params["reporterCode"])]
    data = [{"reporterCode": int(params["reporterCode"]), "period": f"{y}{m:02d}"}
            for y in range(2023, last[0] + 1) for m in range(1, 13) if (y, m) <= last]
    return {"count": len(data), "data": data, "error": ""}


class FakeResponse:
    def __init__(self, status, payload=None, headers=None):
        self.status_code, self._payload, self.headers = status, payload, headers or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    """Devuelve respuestas simuladas; script = lista de códigos HTTP para las primeras llamadas."""
    def __init__(self, script=None, value=100.0):
        self.calls, self.script, self.value = [], list(script or []), value

    def get(self, url, params, timeout, headers):
        self.calls.append((url, dict(params)))
        if self.script:
            status = self.script.pop(0)
            if status != 200:
                return FakeResponse(status, headers={"Retry-After": "0"})
        if url == ec.DA_URL:
            return FakeResponse(200, fake_da(params))
        return FakeResponse(200, fake_data(params, self.value))

    def data_calls(self):
        return [p for u, p in self.calls if u == ec.BASE_URL]


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """Caché temporal, sin esperas, llave falsa; limpia bronze al final."""
    monkeypatch.setattr(ec, "CACHE_DIR", tmp_path / "comtrade")
    monkeypatch.setattr(ec.time, "sleep", lambda s: None)
    monkeypatch.setattr(ec.fetch.retry, "sleep", lambda s: None)
    monkeypatch.setattr(ec, "settings", dataclasses.replace(ec.settings, comtrade_api_key="test-key"))
    yield
    with get_engine("etl").begin() as c:
        c.execute(text(f"DELETE FROM {BRONZE}.raw_api_response WHERE batch_id IN "
                       f"(SELECT batch_id FROM {BRONZE}.extract_batch WHERE params->>'$.start_year' = '1990')"))
        c.execute(text(f"DELETE FROM {BRONZE}.extract_batch WHERE params->>'$.start_year' = '1990'"))


def run(start, end, **kw):
    kw.setdefault("session", FakeSession())
    kw.setdefault("check_availability", False)
    return ec.run(start, end, pause=0, **kw)


def test_plan_counts():
    to_fetch, cached = ec.build_plan(1990, 1992)
    assert len(to_fetch) == N_GROUPS * 3 and cached == []
    p = to_fetch[0].params()
    assert p["period"].startswith("199001,199002") and p["partner2Code"] == 0


def test_mirror_query_is_one_call_for_all_exporters():
    to_fetch, _ = ec.build_plan(1990, 1990)
    mirror = [q for q in to_fetch if q.is_mirror]
    assert len(mirror) == 1
    p = mirror[0].params()
    assert p["partnerCode"] == 156 and p["flowCode"] == "X"
    assert len(p["reporterCode"].split(",")) == len(ec.MIRROR_REPORTERS)


def test_extract_saves_to_bronze_and_cache():
    stats = run(1990, 1990)
    assert stats["fetched"] == N_GROUPS and stats["new_raw"] == N_GROUPS
    assert stats["mirror_records"] == len(ec.MIRROR_REPORTERS) * 12
    assert (ec.CACHE_DIR / "MIRROR_X_1990.json").exists()


def test_rerun_does_not_duplicate_bronze():
    run(1990, 1990)
    assert run(1990, 1990)["new_raw"] == 0


def test_closed_years_come_from_cache():
    run(1990, 1994)
    s = FakeSession()
    stats = run(1990, 1994, session=s)
    assert stats["cached"] == N_GROUPS * 3 and stats["fetched"] == N_GROUPS * 2
    assert sorted({int(p["period"][:4]) for p in s.data_calls()}) == [1993, 1994]


def test_revised_data_enters_as_new_version():
    run(1990, 1990, session=FakeSession(value=100.0))
    assert run(1990, 1990, session=FakeSession(value=101.0))["new_raw"] == N_GROUPS


def test_retries_on_429_then_succeeds():
    s = FakeSession(script=[429, 503])
    stats = run(1990, 1990, session=s)
    assert stats["fetched"] == N_GROUPS and len(s.data_calls()) == N_GROUPS + 2


def test_invalid_key_fails_fast_and_batch_is_failed():
    class Denied(FakeSession):
        def get(self, *a, **k):
            self.calls.append(1)
            return FakeResponse(401)
    s = Denied()
    with pytest.raises(PermissionError):
        run(1990, 1990, session=s)
    assert len(s.calls) == 1
    with get_engine("etl").connect() as c:
        status = c.execute(text(f"SELECT status FROM {BRONZE}.extract_batch "
                                "WHERE params->>'$.start_year'='1990' ORDER BY batch_id DESC LIMIT 1")).scalar()
    assert status == "failed"


def test_api_error_field_raises():
    class ErrSession(FakeSession):
        def get(self, *a, **k):
            return FakeResponse(200, {"data": [], "error": "Invalid parameter"})
    with pytest.raises(RuntimeError, match="Invalid parameter"):
        run(1990, 1990, session=ErrSession())


def test_availability_report_detects_gap(capsys):
    stats = run(1990, 1990, check_availability=True)
    av = stats["availability"]
    assert av[156][-1] == "202412"             # China: último mes publicado
    assert av[218][-1] == "202506"             # Ecuador
    out = capsys.readouterr().out
    assert "CHN (156): último mes publicado 202412" in out
