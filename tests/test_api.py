"""
test_api.py · Fase 11 · API de Pork to China (por HTTP, con TestClient).
Se omite si falta httpx2 (corre .\\setup.ps1) o si gold está vacío (corre .\\pipeline.ps1).
"""
import pytest

pytest.importorskip("httpx2", reason="falta httpx2: corre .\\setup.ps1")
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from src.api.main import app  # noqa: E402
from src.db import get_engine  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with get_engine("bi").connect() as c:
        if not c.execute(text("SELECT COUNT(*) FROM pork_gold.fact_scenario_result")).scalar():
            pytest.skip("gold vacío: corre primero .\\pipeline.ps1")
    return TestClient(app)


def test_health_reports_database_and_last_run(client):
    body = client.get("/health").json()
    # Dentro del pipeline, la última corrida es la que está en curso ('running'): /health la reporta tal cual
    assert body["api"] == "ok" and body["database"] == "ok"
    assert body["last_pipeline_run"]["status"] in ("ok", "running")


def test_scenarios_sorted_by_npv(client):
    s = client.get("/scenarios").json()
    assert len(s) == 24 and s[0]["npv_usd"] >= s[-1]["npv_usd"]


def test_scenario_detail_has_market_and_cashflow(client):
    d = client.get("/scenarios/B-up-4").json()
    assert len(d["market"]) == 10 and len(d["cashflow"]) == 11 and d["scenario"]["code"] == "B-up-4"


def test_tariffs_reproduce_verified_rates(client):
    for month, rate in (("2025-01", 37), ("2025-04", 172), ("2025-07", 57)):
        r = client.get("/tariffs", params={"origin": "usa", "hs": "020649", "month": month})
        assert r.status_code == 200 and r.json()["effective_min_pct"] == rate


def test_booleans_are_json_booleans(client):
    t = client.get("/tariffs", params={"origin": "ECU", "hs": "020649", "month": "2026-01"}).json()
    assert t["has_access"] is False
    assert all(isinstance(r["is_projection"], bool) for r in client.get("/market/china-balance").json())


def test_landed_cost_is_sorted_and_chile_is_cheapest(client):
    sup = client.get("/landed-cost", params={"scenario": "B-up-2"}).json()["suppliers"]
    assert sup[0]["iso3"] == "CHL" and sup == sorted(sup, key=lambda x: x["landed_usd_kg"])


def test_simulate_without_changes_matches_the_pipeline(client):
    """El simulador usa las mismas funciones que el pipeline: sin cambios, el VAN debe ser idéntico."""
    for code in ("B-up-4", "C-down-2", "A-up-6"):
        r = client.post("/simulate", json={"scenario": code}).json()
        assert abs(r["delta_npv_usd"]) < 1, code


def test_simulate_moves_npv_in_the_right_direction(client):
    """Con un valor local de víscera bajo (proyecto rentable), cada palanca mueve el VAN hacia donde debe."""
    good = {"scenario": "B-up-4", "offal_local_value_usd_kg": 0.6}
    base = client.post("/simulate", json=good).json()["npv_usd"]
    worse = client.post("/simulate", json=good | {"offal_local_value_usd_kg": 1.1}).json()["npv_usd"]
    pricier = client.post("/simulate", json=good | {"capex_factor": 2}).json()["npv_usd"]
    cheaper_money = client.post("/simulate", json=good | {"discount_rate": 8}).json()["npv_usd"]
    assert base > 0
    assert worse < base and pricier < base and cheaper_money > base


@pytest.mark.parametrize("method,url,kwargs,status", [
    ("get", "/scenarios/Z-9", {}, 404),
    ("get", "/tariffs", {"params": {"hs": "12"}}, 422),
    ("get", "/tariffs", {"params": {"origin": "ECUA"}}, 422),
    ("get", "/tariffs", {"params": {"month": "2099-01"}}, 404),
    ("post", "/simulate", {"json": {"discount_rate": 99}}, 422),
    ("post", "/simulate", {"json": {"scenario": "Z-9"}}, 404),
])
def test_errors(client, method, url, kwargs, status):
    assert getattr(client, method)(url, **kwargs).status_code == status


def test_openapi_documents_all_routes(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert {"/health", "/scenarios", "/scenarios/{code}", "/tariffs", "/landed-cost",
            "/market/china-balance", "/simulate"} <= set(paths)
