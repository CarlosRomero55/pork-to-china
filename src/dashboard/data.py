"""
data.py · Capa de datos del tablero

Todo se lee de pork_gold con el usuario de SOLO LECTURA (pork_bi), casi siempre de las vistas v_dash_*
y de las tablas de resultados. Las consultas se guardan en caché 10 minutos (st.cache_data): el tablero
no vuelve a la base en cada clic.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:               # Streamlit corre el archivo como script: hace falta la raíz
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
from sqlalchemy import text  # noqa: E402

from src.db import get_engine  # noqa: E402

GOLD = "pork_gold"


@st.cache_resource
def engine():
    return get_engine("bi")


@st.cache_data(ttl=600, show_spinner=False)
def query(sql: str, **params) -> pd.DataFrame:
    with engine().connect() as c:
        df = pd.read_sql(text(sql), c, params=params)
    # MySQL devuelve DECIMAL como objetos Decimal: se pasan a float para graficar
    for col in df.columns:
        if df[col].dtype == object and len(df) and df[col].map(lambda v: hasattr(v, "as_tuple")).any():
            df[col] = df[col].astype(float)
    return df


def china_balance() -> pd.DataFrame:
    return query(f"SELECT * FROM {GOLD}.v_dash_china_balance ORDER BY market_year")


def sam_yearly() -> pd.DataFrame:
    return query(f"SELECT * FROM {GOLD}.v_dash_sam_yearly ORDER BY year")


def trade_diversion(group: str) -> pd.DataFrame:
    """Cambio de participación 12 meses antes vs 12 meses después del arancel a EE. UU. (base espejo)."""
    sql = (ROOT / "sql" / "queries" / "q01_trade_diversion.sql").read_text(encoding="utf-8")
    df = query(sql)
    return df[df["grupo"] == group].sort_values("cambio_pp")


def scenarios() -> pd.DataFrame:
    return query(f"""
        SELECT s.code, s.trade_case, s.china_selfsuff, s.cert_year, s.label_es,
               r.npv_usd, r.irr_pct, r.payback_years, r.breakeven_offal_usd_kg, r.fx_usd, r.jobs
        FROM {GOLD}.dim_scenario s JOIN {GOLD}.fact_scenario_result r ON r.scenario_key = s.scenario_key""")


def offal_local_value() -> float:
    """Valor local base de la víscera (USD/kg) que usan los escenarios."""
    d = query(f"SELECT MAX(value) AS v FROM {GOLD}.v_scenario_params WHERE name = 'offal_local_value_usd_kg'")
    return float(d["v"].iloc[0])


def cashflows() -> pd.DataFrame:
    return query(f"""
        SELECT s.code, c.year_n, c.net_cashflow, c.discounted_cf, c.cumulative_dcf, c.tonnes
        FROM {GOLD}.fact_scenario_cashflow c JOIN {GOLD}.dim_scenario s ON s.scenario_key = c.scenario_key
        ORDER BY s.code, c.year_n""")


def landed_cost(code: str, hs: str) -> pd.DataFrame:
    return query(f"""
        SELECT c.iso3, c.name_es AS supplier, c.exports_pork_to_china AS has_access,
               l.fob_usd_kg, l.freight_usd_kg + l.insurance_usd_kg AS freight_ins_usd_kg,
               l.landed_usd_kg - l.cif_usd_kg AS duty_usd_kg, l.total_duty_pct, l.landed_usd_kg
        FROM {GOLD}.fact_landed_cost l
        JOIN {GOLD}.dim_scenario s ON s.scenario_key = l.scenario_key AND s.code = :code
        JOIN {GOLD}.dim_country c ON c.country_key = l.supplier_key
        JOIN {GOLD}.dim_product p ON p.product_key = l.product_key AND p.hs_code = :hs
        ORDER BY l.landed_usd_kg DESC""", code=code, hs=hs)


def province_pigs() -> pd.DataFrame:
    return query(f"""SELECT * FROM {GOLD}.v_dash_province_pigs
                    WHERE survey_year = (SELECT MAX(survey_year) FROM {GOLD}.v_dash_province_pigs)""")


def sanitary() -> pd.DataFrame:
    return query(f"SELECT * FROM {GOLD}.v_dash_sanitary ORDER BY FIELD(china_risk, 'bloquea', 'en camino', 'favorable')")


def access_benchmark() -> pd.DataFrame:
    return query(f"SELECT * FROM {GOLD}.v_dash_access_benchmark ORDER BY FIELD(iso3, 'CHL', 'CRI', 'BRA', 'ECU')")


def policy_events() -> pd.DataFrame:
    return query(f"SELECT * FROM {GOLD}.v_dash_policy_events ORDER BY event_date")


def offal_monthly_us_vs_rest() -> pd.DataFrame:
    """Importaciones chinas de vísceras por mes (datos espejo): EE. UU. frente al resto de proveedores."""
    return query(f"""
        SELECT date, CASE WHEN iso3 = 'USA' THEN 'EE. UU.' ELSE 'Resto de proveedores' END AS who,
               SUM(tonnes) AS tonnes, MIN(month_is_complete) AS complete
        FROM {GOLD}.v_dash_supplier_monthly
        WHERE product_group = 'Vísceras'
        GROUP BY date, who ORDER BY date""")


def its_series(model: str) -> pd.DataFrame:
    return query(f"SELECT * FROM {GOLD}.fact_its_series WHERE model = :m ORDER BY date", m=model)


def its_coef() -> pd.DataFrame:
    return query(f"SELECT * FROM {GOLD}.fact_its_coef")


def mc_summary() -> pd.DataFrame:
    return query(f"""SELECT m.*, s.code, s.trade_case, s.china_selfsuff, s.cert_year
                     FROM {GOLD}.fact_mc_summary m JOIN {GOLD}.dim_scenario s USING (scenario_key)""")


def mc_hist(key: int) -> pd.DataFrame:
    return query(f"SELECT * FROM {GOLD}.fact_mc_hist WHERE scenario_key = :k ORDER BY bin", k=key)


def mc_tornado(key: int) -> pd.DataFrame:
    return query(f"SELECT * FROM {GOLD}.fact_mc_tornado WHERE scenario_key = :k ORDER BY swing", k=key)


def last_run() -> pd.DataFrame:
    return query(f"SELECT run_id, finished_at, status FROM {GOLD}.v_last_pipeline_run")


def triggers() -> pd.DataFrame:
    return query(f"SELECT * FROM {GOLD}.fact_trigger ORDER BY sort_order")
