"""
main.py · Fase 11 · API de Pork to China (FastAPI)

Sirve por HTTP los resultados del modelo gold y un simulador What-If. Todas las consultas usan el
usuario de SOLO LECTURA pork_bi (SELECT sobre pork_gold); /simulate no escribe nada: recalcula en
memoria con las mismas funciones de src/finance.py que usa el pipeline, así el cálculo vive en un
solo lugar.

Levantarla:  uvicorn src.api.main:app --port 8000      (o .\\api.ps1)
Documentación interactiva:  http://127.0.0.1:8000/docs
"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from src import finance as fi
from src.db import get_engine
from src.scenarios import ramp_share, volume

GOLD = "pork_gold"
app = FastAPI(
    title="Pork to China · API",
    version="1.0.0",
    description=(
        "¿Puede Ecuador aprovechar la guerra comercial para vender cerdo a China? "
        "Esta API sirve el modelo del proyecto (datos de UN Comtrade y USDA, aranceles con historia SCD2, "
        "24 escenarios y el flujo de caja de AgroPorc, una empresa ficticia) y un simulador What-If.\n\n"
        "Todos los montos están en USD; los volúmenes, en toneladas de peso neto."),
)


# ---------------------------------------------------------------- acceso a datos
@lru_cache(maxsize=1)
def engine():
    return get_engine("bi")


# MySQL guarda BOOLEAN como TINYINT (0/1); estas columnas se devuelven como true/false en el JSON
BOOL_COLS = {"has_access", "is_projection", "is_sam", "month_is_complete", "is_outlier", "is_estimate"}


def rows(sql: str, **params) -> list[dict]:
    """Ejecuta una consulta de solo lectura y devuelve filas como diccionarios con tipos JSON."""
    with engine().connect() as c:
        res = c.execute(text(sql), params)
        cols = list(res.keys())
        return [{k: (bool(v) if k in BOOL_COLS and v is not None else _json(v)) for k, v in zip(cols, r)}
                for r in res]


def _json(v):
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (date,)):
        return v.isoformat()
    return v


def scenario_key(code: str) -> int:
    hit = rows(f"SELECT scenario_key FROM {GOLD}.dim_scenario WHERE code = :c", c=code)
    if not hit:
        raise HTTPException(404, f"Escenario desconocido: {code}. Ver GET /scenarios")
    return hit[0]["scenario_key"]


# ---------------------------------------------------------------- endpoints de lectura
@app.get("/health", tags=["estado"], summary="Estado de la API, de la base y de la última corrida del pipeline")
def health():
    try:
        run = rows(f"SELECT run_id, started_at, finished_at, status FROM {GOLD}.v_last_pipeline_run")
    except Exception as e:                              # la base no responde: la API sigue viva y lo dice
        return {"api": "ok", "database": "error", "detail": type(e).__name__}
    return {"api": "ok", "database": "ok", "last_pipeline_run": run[0] if run else None}


@app.get("/scenarios", tags=["escenarios"], summary="Los 24 escenarios con su VAN, TIR y payback")
def list_scenarios():
    return rows(f"""
        SELECT s.code, s.trade_case, s.china_selfsuff, s.cert_year, s.label_es,
               r.npv_usd, r.irr_pct, r.payback_years, r.discounted_payback_years,
               r.breakeven_offal_usd_kg, r.breakeven_tonnes, r.fx_usd, r.jobs
        FROM {GOLD}.dim_scenario s JOIN {GOLD}.fact_scenario_result r ON r.scenario_key = s.scenario_key
        ORDER BY r.npv_usd DESC""")


@app.get("/scenarios/{code}", tags=["escenarios"], summary="Un escenario: resultado, mercado y flujo de caja año a año")
def get_scenario(code: str):
    key = scenario_key(code)
    head = rows(f"""SELECT s.code, s.trade_case, s.china_selfsuff, s.cert_year, s.label_es, r.*
                    FROM {GOLD}.dim_scenario s JOIN {GOLD}.fact_scenario_result r ON r.scenario_key = s.scenario_key
                    WHERE s.scenario_key = :k""", k=key)[0]
    head.pop("scenario_key", None)
    return {
        "scenario": head,
        "market": rows(f"""SELECT year_n, calendar_year, tam_t, sam_t, som_cap_t, capacity_t, agroporc_t, binding,
                                  ecuador_duty_pct FROM {GOLD}.fact_scenario_market WHERE scenario_key = :k
                           ORDER BY year_n""", k=key),
        "cashflow": rows(f"""SELECT year_n, tonnes, capex, revenue, opex, net_cashflow, discounted_cf, cumulative_dcf
                             FROM {GOLD}.fact_scenario_cashflow WHERE scenario_key = :k ORDER BY year_n""", k=key),
    }


@app.get("/tariffs", tags=["aranceles"], summary="Arancel efectivo de China por origen, línea HS y mes")
def tariffs(origin: str = Query("ECU", pattern=r"^[A-Za-z]{3}$", description="Código ISO3 del origen", examples=["ECU"]),
            hs: str = Query("020649", pattern=r"^\d{6}$", description="Línea HS de 6 dígitos", examples=["020649"]),
            month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$", description="AAAA-MM; por defecto, el mes actual")):
    month = month or date.today().strftime("%Y-%m")
    hit = rows(f"""SELECT year_month_label AS month, iso3, origin, has_access, hs_code, product_group, mfn_pct,
                          preferential_pct, additional_pct, antidumping_min_pct, antidumping_max_pct,
                          effective_min_pct, effective_max_pct
                   FROM {GOLD}.v_dash_tariff
                   WHERE iso3 = :o AND hs_code = :h AND DATE_FORMAT(date, '%Y-%m') = :m""",
               o=origin.upper(), h=hs, m=month)
    if not hit:
        raise HTTPException(404, f"Sin datos para {origin.upper()} · {hs} · {month} (el modelo cubre 2018-01 a 2032-12)")
    return hit[0]


@app.get("/landed-cost", tags=["costos"], summary="Costo puesto en China por proveedor en un escenario")
def landed_cost(scenario: str = Query("B-up-2", examples=["B-up-2"]),
                hs: str = Query("020649", pattern=r"^\d{6}$")):
    key = scenario_key(scenario)
    data = rows(f"""SELECT c.iso3, c.name_es AS supplier, c.exports_pork_to_china AS has_access,
                           l.fob_usd_kg, l.freight_usd_kg, l.insurance_usd_kg, l.cif_usd_kg, l.total_duty_pct,
                           l.landed_usd_kg, l.gap_vs_best_usd_kg
                    FROM {GOLD}.fact_landed_cost l
                    JOIN {GOLD}.dim_country c ON c.country_key = l.supplier_key
                    JOIN {GOLD}.dim_product p ON p.product_key = l.product_key
                    WHERE l.scenario_key = :k AND p.hs_code = :h ORDER BY l.landed_usd_kg""", k=key, h=hs)
    if not data:
        raise HTTPException(404, f"Sin costo puesto en China para la línea {hs}")
    return {"scenario": scenario, "hs_code": hs, "suppliers": data}


@app.get("/market/china-balance", tags=["mercado"], summary="Balance de cerdo de China (USDA, miles de t CWE)")
def china_balance():
    return rows(f"SELECT * FROM {GOLD}.v_dash_china_balance ORDER BY market_year")


# ---------------------------------------------------------------- simulador What-If
class SimulationInput(BaseModel):
    """Supuestos que se pueden mover. Lo que no se envía conserva el valor del escenario."""
    scenario: str = Field("B-up-4", description="Escenario de partida", examples=["B-up-4"])
    discount_rate: float | None = Field(None, ge=0, le=40, description="Tasa de descuento (%)")
    offal_local_value_usd_kg: float | None = Field(None, ge=0, le=5, description="Valor local de la víscera (USD/kg)")
    fob_usd_kg: float | None = Field(None, gt=0, le=10, description="Precio FOB de venta (USD/kg)")
    capacity_t: float | None = Field(None, ge=0, le=50000, description="Capacidad anual de AgroPorc (t)")
    capex_factor: float = Field(1.0, gt=0, le=5, description="Multiplica toda la inversión (1 = base)")


class SimulationOutput(BaseModel):
    scenario: str
    npv_usd: float
    irr_pct: float | None
    payback_years: float | None
    breakeven_offal_usd_kg: float | None
    total_tonnes: float
    base_npv_usd: float
    delta_npv_usd: float
    assumptions_used: dict[str, float]


@app.post("/simulate", tags=["simulador"], response_model=SimulationOutput,
          summary="Recalcula VAN y TIR de un escenario cambiando supuestos (no guarda nada)")
def simulate(inp: SimulationInput):
    key = scenario_key(inp.scenario)
    p = {r["name"]: r["value"] for r in rows(f"SELECT name, value FROM {GOLD}.v_scenario_params "
                                               f"WHERE scenario_key = :k", k=key)}
    cert = rows(f"SELECT cert_year FROM {GOLD}.dim_scenario WHERE scenario_key = :k", k=key)[0]["cert_year"]
    caps = [r["som_cap_t"] for r in rows(f"SELECT som_cap_t FROM {GOLD}.fact_scenario_market "
                                          f"WHERE scenario_key = :k ORDER BY year_n", k=key)]
    base_npv = rows(f"SELECT npv_usd FROM {GOLD}.fact_scenario_result WHERE scenario_key = :k", k=key)[0]["npv_usd"]

    overrides = {"discount_rate": inp.discount_rate, "offal_local_value_usd_kg": inp.offal_local_value_usd_kg,
                 "ecuador_fob_usd_kg_offal": inp.fob_usd_kg, "agroporc_capacity_t": inp.capacity_t}
    p |= {k: v for k, v in overrides.items() if v is not None}
    for k in fi.CAPEX_ITEMS:
        p[k] = p[k] * inp.capex_factor
    # Mismo volumen que el pipeline: mín(capacidad × rampa, techo de mercado del escenario)
    tonnes = [volume(p["agroporc_capacity_t"] * ramp_share(n, cert, p["entry_ramp_y1_pct"], p["entry_ramp_y2_pct"]),
                     cap)[0] for n, cap in enumerate(caps, start=1)]
    res, _ = fi.evaluate(tonnes, p, cert)
    shown = ("discount_rate", "offal_local_value_usd_kg", "ecuador_fob_usd_kg_offal", "agroporc_capacity_t")
    return SimulationOutput(
        scenario=inp.scenario, npv_usd=res["npv_usd"], irr_pct=res["irr_pct"], payback_years=res["payback_years"],
        breakeven_offal_usd_kg=res["breakeven_offal_usd_kg"], total_tonnes=round(sum(tonnes), 1),
        base_npv_usd=base_npv, delta_npv_usd=round(res["npv_usd"] - base_npv, 2),
        assumptions_used={k: p[k] for k in shown} | {"capex_usd": sum(p[k] for k in fi.CAPEX_ITEMS)})
