"""
test_gold.py · Fase 7 · reglas del modelo gold.
Las funciones de cálculo se prueban con datos sintéticos (sin base de datos);
al final, una prueba de integración revisa el gold construido (se omite si está vacío).
"""
import pandas as pd
import pytest
from sqlalchemy import text

from src import build_gold as bg
from src.db import GOLD, get_engine

FAR = "9999-12-31"
US, ES, GB, EC, CL = 1, 2, 3, 4, 5          # ids sintéticos de países
EU = 10                                     # id sintético del bloque


def measure(hs, mtype, rate, vfrom, vto=FAR, target=None, group=None, company=None):
    return dict(hs_code=hs, measure_type=mtype, rate_pct=rate, valid_from=vfrom, valid_to=vto,
                target_id=target, target_group_id=group, target_company=company)


@pytest.fixture()
def tariffs():
    m = pd.DataFrame([
        measure("020649", "mfn", 12, "2018-01-01"),
        measure("020649", "retaliatory_232", 25, "2018-04-02", target=US),
        measure("020649", "reciprocal", 125, "2025-04-12", "2025-05-13", target=US),
        measure("020649", "antidumping", 4.9, "2025-12-17", group=EU, company="(mín)"),
        measure("020649", "antidumping", 19.8, "2025-12-17", group=EU, company="(máx)"),
        measure("020649", "antidumping", 4.9, "2025-12-17", group=EU, company="(mín, duplicado)"),
        measure("020649", "preferential", 9.6, "2026-01-01", target=EC),
        measure("020649", "preferential", 0, "2018-01-01", target=CL),
    ])
    members = pd.DataFrame([
        dict(group_id=EU, country_id=ES, valid_from="1986-01-01", valid_to=FAR),
        dict(group_id=EU, country_id=GB, valid_from="1973-01-01", valid_to="2020-01-31"),
    ])
    months = pd.Series(pd.date_range("2025-01-01", "2026-12-01", freq="MS"))
    out = bg.applied_tariffs(m, members, months, [US, ES, GB, EC, CL], ["020649"])
    return out.set_index(["date_key", "origin_id"])


def test_rate_is_the_one_in_force_on_day_15(tariffs):
    assert tariffs.loc[(20250401, US), "total_min_pct"] == 12 + 25 + 125   # recíproco desde el 12-abr
    assert tariffs.loc[(20250501, US), "total_min_pct"] == 12 + 25         # terminó el 13-may (antes del 15)


def test_group_measures_follow_membership_dates(tariffs):
    assert tariffs.loc[(20260101, ES), "antidumping_max_pct"] == 19.8
    assert pd.isna(tariffs.loc[(20260101, GB), "antidumping_max_pct"])     # el Reino Unido salió de la UE


def test_company_rates_are_a_range_not_a_sum(tariffs):
    row = tariffs.loc[(20260101, ES)]
    assert (row["antidumping_min_pct"], row["antidumping_max_pct"]) == (4.9, 19.8)   # duplicado no suma
    assert (row["total_min_pct"], row["total_max_pct"]) == (12 + 4.9, 12 + 19.8)


def test_preferential_replaces_mfn(tariffs):
    assert tariffs.loc[(20260601, EC), "effective_min_pct"] == 9.6        # no 12 + 9,6
    assert tariffs.loc[(20250601, EC), "effective_min_pct"] == 12         # antes del acuerdo
    assert tariffs.loc[(20250601, CL), "effective_min_pct"] == 0


def test_missing_mfn_is_an_error():
    m = pd.DataFrame([measure("020649", "mfn", 12, "2018-01-01")])
    with pytest.raises(ValueError, match="sin NMF"):
        bg.applied_tariffs(m, pd.DataFrame(columns=["group_id", "country_id", "valid_from", "valid_to"]),
                           pd.Series(pd.to_datetime(["2025-01-01"])), [US], ["020649", "020329"])


def test_shares_are_computed_within_each_basis():
    flows = pd.DataFrame([
        dict(date="2025-01-01", supplier_id=US, hs_code="020649", basis="direct", net_weight_kg=3000, value_usd=6000, quality_flag=None),
        dict(date="2025-01-01", supplier_id=ES, hs_code="020649", basis="direct", net_weight_kg=1000, value_usd=2000, quality_flag="outlier_unit_value"),
        dict(date="2025-01-01", supplier_id=US, hs_code="020649", basis="mirror", net_weight_kg=5000, value_usd=9000, quality_flag=None),
    ])
    out = bg.shape_imports(flows, {"020649": 1}).set_index(["partner_key", "basis"])
    assert out.loc[(US, "direct"), "share_pct"] == 75 and out.loc[(US, "mirror"), "share_pct"] == 100
    assert out.loc[(US, "direct"), "unit_value_usd_kg"] == 2 and out.loc[(ES, "direct"), "is_outlier"]


def test_access_window_is_measured_per_basis():
    dims = pd.DataFrame({"country_key": [US, CL, EC]})
    imports = pd.DataFrame([
        dict(date_key=20241201, partner_key=CL, basis="direct", tonnes=10.0),   # solo en directo
        dict(date_key=20260901, partner_key=US, basis="mirror", tonnes=5.0),
        dict(date_key=20200101, partner_key=EC, basis="mirror", tonnes=1.0),    # demasiado antiguo
    ])
    got = bg.with_access(dims, imports).set_index("country_key")["exports_pork_to_china"]
    assert got[US] and got[CL] and not got[EC]


def test_built_gold_reconciles_with_silver():
    """Integración: si gold ya se construyó, debe cuadrar con silver y con el arancel verificado."""
    with get_engine("etl").connect() as conn:
        if not conn.execute(text(f"SELECT COUNT(*) FROM {GOLD}.fact_tariff_applied")).scalar():
            pytest.skip("gold vacío: corre primero .\\gold.ps1")
        assert bg.reconcile(conn)
