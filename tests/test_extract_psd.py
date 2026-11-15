"""
test_extract_psd.py · Extractor USDA PSD con una API simulada (no llama a USDA).
"""
import dataclasses

import pytest
from sqlalchemy import text

import src.extract_psd as ep
from src.db import BRONZE, get_engine

COMMODITIES = [{"commodityCode": "0111000", "commodityName": "Meat, Beef and Veal"},
               {"commodityCode": "0113000", "commodityName": "Meat, Swine"}]
COUNTRIES = [{"countryCode": "CH", "countryName": "China"}, {"countryCode": "EC", "countryName": "Ecuador"}]
ATTRS = [{"attributeId": 28, "attributeName": "Production"}, {"attributeId": 57, "attributeName": "Imports"}]
UNITS = [{"unitId": 21, "unitDescription": "(1000 MT CWE)"}]


def data(year):
    return [{"commodityCode": "0113000", "countryCode": "CH", "marketYear": str(year), "calendarYear": "2026",
             "month": "10", "attributeId": 28, "unitId": 21, "value": 59000.0},
            {"commodityCode": "0113000", "countryCode": "CH", "marketYear": str(year), "calendarYear": "2026",
             "month": "10", "attributeId": 57, "unitId": 21, "value": 1100.0}]


class Resp:
    def __init__(self, status, payload=None):
        self.status_code, self._p = status, payload

    def json(self):
        return self._p

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class FakeSession:
    def __init__(self, script=None):
        self.calls, self.script = [], list(script or [])

    def get(self, url, timeout, headers):
        self.calls.append((url, headers))
        if self.script:
            s = self.script.pop(0)
            if s != 200:
                return Resp(s)
        path = url.split("/api/psd/")[1]
        ref = {"commodities": COMMODITIES, "countries": COUNTRIES,
               "commodityAttributes": ATTRS, "unitsOfMeasure": UNITS}
        if path in ref:
            return Resp(200, ref[path])
        year = int(path.rsplit("/", 1)[1])
        return Resp(200, data(year))


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(ep, "CACHE_DIR", tmp_path / "psd")
    monkeypatch.setattr(ep.time, "sleep", lambda s: None)
    monkeypatch.setattr(ep.get_json.retry, "sleep", lambda s: None)
    monkeypatch.setattr(ep, "settings", dataclasses.replace(ep.settings, usda_fas_api_key="test-key"))
    yield
    with get_engine("etl").begin() as c:
        c.execute(text(f"DELETE FROM {BRONZE}.raw_api_response WHERE batch_id IN (SELECT batch_id FROM "
                       f"{BRONZE}.extract_batch WHERE source_name='usda_psd' AND params->>'$.start_year'='1990')"))
        c.execute(text(f"DELETE FROM {BRONZE}.extract_batch WHERE source_name='usda_psd' "
                       "AND params->>'$.start_year'='1990'"))


def test_finds_pork_code_in_catalog():
    assert ep.find_pork_code(COMMODITIES) == ("0113000", "Meat, Swine")
    assert ep.find_pork_code([{"CommodityCode": "X1", "CommodityName": "Pork Meat"}])[0] == "X1"
    assert ep.find_pork_code([])[0] == ep.FALLBACK_PORK_CODE


def test_run_saves_reference_and_years(capsys):
    s = FakeSession()
    stats = ep.run(1990, 1991, session=s, pause=0)
    assert stats["calls"] == 4 + 2 * 2
    assert all(h["API_KEY"] == "test-key" for _, h in s.calls)       # la llave va en el encabezado
    assert any("/commodity/0113000/country/all/year/1991" in u for u, _ in s.calls)
    out = capsys.readouterr().out
    assert "Atributos disponibles para China: ['Imports', 'Production']" in out
    assert (ep.CACHE_DIR / "commodity_0113000_world_year_1990.json").exists()


def test_rerun_does_not_duplicate():
    ep.run(1990, 1990, session=FakeSession(), pause=0)
    assert ep.run(1990, 1990, session=FakeSession(), pause=0)["new_raw"] == 0


def test_retries_then_succeeds():
    s = FakeSession(script=[429, 503])
    assert ep.run(1990, 1990, session=s, pause=0)["calls"] == 6


def test_invalid_key_fails_fast():
    s = FakeSession(script=[403])
    with pytest.raises(PermissionError):
        ep.run(1990, 1990, session=s, pause=0)
    assert len(s.calls) == 1
