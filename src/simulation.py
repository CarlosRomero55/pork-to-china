"""
simulation.py · Simulador What-If compartido (Fase 11–12)

Una sola implementación para la API (POST /simulate) y para el tablero de Streamlit: recalcula el VAN,
la TIR y el payback de un escenario cambiando supuestos, con las mismas funciones del pipeline
(src/scenarios.py para el volumen y src/finance.py para el flujo de caja). No escribe nada en la base.
Lee solo de pork_gold con el usuario de solo lectura (pork_bi).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from sqlalchemy import text

from src import finance as fi
from src.db import get_engine
from src.scenarios import ramp_share, volume

GOLD = "pork_gold"

# Supuestos que el usuario puede mover → nombre del supuesto en el modelo
OVERRIDABLE = {"discount_rate": "discount_rate", "offal_local_value_usd_kg": "offal_local_value_usd_kg",
               "fob_usd_kg": "ecuador_fob_usd_kg_offal", "capacity_t": "agroporc_capacity_t"}


class UnknownScenario(KeyError):
    pass


@dataclass(frozen=True)
class ScenarioInputs:
    code: str
    cert_year: int | None
    params: dict
    market_caps: tuple[float, ...]          # techo de mercado de cada año (t)
    base_npv: float


@dataclass
class SimulationResult:
    scenario: str
    npv_usd: float
    irr_pct: float | None
    payback_years: float | None
    breakeven_offal_usd_kg: float | None
    total_tonnes: float
    base_npv_usd: float
    delta_npv_usd: float
    tonnes_by_year: list[float] = field(default_factory=list)
    assumptions_used: dict[str, float] = field(default_factory=dict)


@lru_cache(maxsize=1)
def _engine():
    return get_engine("bi")


def load(code: str) -> ScenarioInputs:
    """Lee de gold todo lo que necesita la simulación de un escenario."""
    with _engine().connect() as c:
        row = c.execute(text(f"SELECT scenario_key, cert_year FROM {GOLD}.dim_scenario WHERE code = :c"),
                        {"c": code}).first()
        if row is None:
            raise UnknownScenario(code)
        key, cert = row
        params = {n: float(v) for n, v in c.execute(text(
            f"SELECT name, value FROM {GOLD}.v_scenario_params WHERE scenario_key = :k"), {"k": key})}
        caps = tuple(float(v) for (v,) in c.execute(text(
            f"SELECT som_cap_t FROM {GOLD}.fact_scenario_market WHERE scenario_key = :k ORDER BY year_n"), {"k": key}))
        base = float(c.execute(text(f"SELECT npv_usd FROM {GOLD}.fact_scenario_result WHERE scenario_key = :k"),
                               {"k": key}).scalar())
    return ScenarioInputs(code, None if cert is None else int(cert), params, caps, base)


def run(inp: ScenarioInputs, capex_factor: float = 1.0, **overrides: float | None) -> SimulationResult:
    """Recalcula el escenario con los supuestos cambiados (los None conservan el valor del escenario)."""
    p = dict(inp.params)
    for arg, value in overrides.items():
        if value is not None:
            p[OVERRIDABLE[arg]] = float(value)
    for k in fi.CAPEX_ITEMS:
        p[k] = p[k] * capex_factor
    # Mismo volumen que el pipeline: mín(capacidad × rampa, techo de mercado del escenario)
    tonnes = [volume(p["agroporc_capacity_t"] * ramp_share(n, inp.cert_year, p["entry_ramp_y1_pct"],
                                                           p["entry_ramp_y2_pct"]), cap)[0]
              for n, cap in enumerate(inp.market_caps, start=1)]
    res, _ = fi.evaluate(tonnes, p, inp.cert_year)
    shown = ("discount_rate", "offal_local_value_usd_kg", "ecuador_fob_usd_kg_offal", "agroporc_capacity_t")
    return SimulationResult(
        scenario=inp.code, npv_usd=res["npv_usd"], irr_pct=res["irr_pct"], payback_years=res["payback_years"],
        breakeven_offal_usd_kg=res["breakeven_offal_usd_kg"], total_tonnes=round(sum(tonnes), 1),
        base_npv_usd=inp.base_npv, delta_npv_usd=round(res["npv_usd"] - inp.base_npv, 2),
        tonnes_by_year=[round(t, 1) for t in tonnes],
        assumptions_used={k: p[k] for k in shown} | {"capex_usd": sum(p[k] for k in fi.CAPEX_ITEMS)})
