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
        c.execute(text(f"DELETE FROM {BRONZE}.raw_file WHERE batch_id IN (SELECT batch_id FROM "
                       f"{BRONZE}.extract_batch WHERE source_name='usda_psd' AND params->>'$.start_year'='1990')"))
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
    s = FakeSession(script=[200, 429, 503])          # 1ª = verificación rápida de la API
    assert ep.run(1990, 1990, session=s, pause=0)["calls"] == 6


def test_invalid_key_fails_fast():
    s = FakeSession(script=[200, 403])               # la API responde, pero rechaza la llave en catálogos
    with pytest.raises(PermissionError):
        ep.run(1990, 1990, session=s, pause=0)
    assert len(s.calls) == 2


def test_missing_catalog_does_not_stop_extraction(capsys):
    """Si un catálogo da 500 de forma persistente, se sigue con los datos."""
    class CatalogDown(FakeSession):
        def get(self, url, timeout, headers):
            if url.endswith("/commodities"):
                self.calls.append((url, headers))
                return Resp(500)
            return super().get(url, timeout, headers)
    s = CatalogDown()
    stats = ep.run(1990, 1990, session=s, pause=0)
    assert stats["missing_refs"] == ["commodities"]
    assert any("/commodity/0113000/country/all/year/1990" in u for u, _ in s.calls)   # usó el código por defecto
    assert "NO DISPONIBLE" in capsys.readouterr().out


def test_probe_masks_key(capsys):
    class Echo(FakeSession):
        def get(self, url, timeout, headers):
            r = Resp(500)
            r.text = f"error con llave test-key en {url}"
            r.headers = {"Content-Type": "text/html"}
            return r
    ep.probe(Echo(), "test-key")
    out = capsys.readouterr().out
    assert "test-key" not in out and "***" in out and out.count("[500]") == 5 + len(ep.BULK_URLS) * len(ep.BULK_HEADER_VARIANTS)


# ---------------------------------------------------------------- descarga masiva
import io as _io
import zipfile as _zip

CSV = ("Commodity_Code,Commodity_Description,Country_Code,Country_Name,Market_Year,Calendar_Year,Month,"
       "Attribute_ID,Attribute_Description,Unit_ID,Unit_Description,Value\n"
       "0113000,\"Meat, Swine\",CH,China,1990,2026,10,28,Production,21,(1000 MT CWE),59000\n"
       "0113000,\"Meat, Swine\",CH,China,1990,2026,10,57,Imports,21,(1000 MT CWE),1100\n"
       "0113000,\"Meat, Swine\",CH,China,1990,2026,10,125,Domestic Consumption,21,(1000 MT CWE),60000\n"
       "0113000,\"Meat, Swine\",EC,Ecuador,1990,2026,10,28,Production,21,(1000 MT CWE),240\n"
       "0111000,\"Meat, Beef and Veal\",CH,China,1990,2026,10,28,Production,21,(1000 MT CWE),7700\n")


def make_zip(csv=CSV):
    buf = _io.BytesIO()
    with _zip.ZipFile(buf, "w") as z:
        z.writestr("psd_livestock.csv", csv)
    return buf.getvalue()


class BulkResp(Resp):
    def __init__(self, status, content=b"", ctype="application/zip"):
        super().__init__(status)
        self.content, self.headers = content, {"Content-Type": ctype}


class ApiDownBulkUp:
    """La API responde 500; la descarga masiva funciona (opcionalmente la 1ª URL da 404)."""
    def __init__(self, first_404=False):
        self.calls, self.first_404 = [], first_404

    def get(self, url, timeout, headers):
        self.calls.append(url)
        if "/OpenData/" in url:
            return BulkResp(500, b'{"message":"An error has occurred."}', "application/json")
        if self.first_404 and url == ep.BULK_URLS[0]:
            return BulkResp(404, b"not found", "text/html")
        return BulkResp(200, make_zip())


def test_falls_back_to_bulk_when_api_down(capsys):
    stats = ep.run(1990, 1990, session=ApiDownBulkUp(), pause=0)
    assert stats["mode"] == "bulk" and stats["records"] == 4          # 4 filas de cerdo, la de res se filtra
    out = capsys.readouterr().out
    assert "DESCARGA MASIVA" in out and "Atributos de China: ['Domestic Consumption', 'Imports', 'Production']" in out
    assert (ep.CACHE_DIR / "psd_livestock_csv.zip").exists()


def test_bulk_same_file_is_not_duplicated():
    assert ep.run(1990, 1990, session=ApiDownBulkUp(), pause=0)["new_raw"] == 1
    assert ep.run(1990, 1990, session=ApiDownBulkUp(), pause=0)["new_raw"] == 0


def test_bulk_tries_next_url():
    s = ApiDownBulkUp(first_404=True)
    stats = ep.run(1990, 1990, session=s, pause=0)
    assert stats["records"] == 4 and ep.BULK_URLS[1] in s.calls


def test_read_pork_only():
    df = ep.read_pork_from_zip(make_zip())
    assert set(df["commoditydescription"]) == {"Meat, Swine"} and len(df) == 4


class PickyServer(ApiDownBulkUp):
    """Simula el servidor real: 406 salvo que el cliente se identifique como navegador."""
    def get(self, url, timeout, headers):
        self.calls.append((url, dict(headers)))
        if "/OpenData/" in url:
            return BulkResp(500, b"{}", "application/json")
        if "Mozilla" not in headers.get("User-Agent", ""):
            return BulkResp(406, b"Not Acceptable", "text/html")
        return BulkResp(200, make_zip())


def test_bulk_retries_with_other_headers_on_406(capsys):
    s = PickyServer()
    stats = ep.run(1990, 1990, session=s, pause=0)
    assert stats["records"] == 4
    assert "descarga OK con 'Accept: */* + navegador'" in capsys.readouterr().out


def test_bulk_rejects_html_disguised_as_success():
    class HtmlInstead(ApiDownBulkUp):
        def get(self, url, timeout, headers):
            if "/OpenData/" in url:
                return BulkResp(500, b"{}", "application/json")
            return BulkResp(200, b"<html>mantenimiento</html>", "text/html")
    with pytest.raises(RuntimeError, match="no es un ZIP"):
        ep.run(1990, 1990, session=HtmlInstead(), pause=0)
