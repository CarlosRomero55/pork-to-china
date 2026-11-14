"""
test_clean.py · Limpieza de Comtrade (funciones puras, sin base de datos).
"""
from datetime import date

import pandas as pd

from src.clean import flag_unit_value_outliers, parse_comtrade, quality_summary


def rec(**kw):
    base = {"period": "202503", "reporterCode": 156, "partnerCode": 842, "cmdCode": "020649",
            "flowCode": "M", "partner2Code": 0, "customsCode": "C00", "motCode": 0,
            "netWgt": 1000.0, "primaryValue": 2000.0, "isNetWgtEstimated": False}
    base.update(kw)
    return base


def test_parse_basic_fields():
    df = parse_comtrade({"data": [rec()]})
    row = df.iloc[0]
    assert row["period"] == date(2025, 3, 1)
    assert row["hs_code"] == "020649" and row["flow_type"] == "M"
    assert row["net_weight_kg"] == 1000.0 and row["value_usd"] == 2000.0


def test_parse_keeps_only_totals():
    """Filas desglosadas por aduana o transporte duplicarían el volumen: se descartan."""
    df = parse_comtrade({"data": [rec(), rec(customsCode="C01"), rec(motCode=2100), rec(partner2Code=344)]})
    assert len(df) == 1


def test_zero_weight_becomes_null():
    """Peso 0 significa 'no informado', no 'cero toneladas'."""
    df = parse_comtrade({"data": [rec(netWgt=0), rec(netWgt=None)]})
    assert df["net_weight_kg"].isna().all()


def test_hs_code_keeps_leading_zero():
    df = parse_comtrade({"data": [rec(cmdCode=20649)]})
    assert df.iloc[0]["hs_code"] == "020649"


def test_empty_payload():
    assert parse_comtrade({"count": 0, "data": [], "error": ""}).empty


def test_outlier_flag_is_relative_to_its_group():
    # 20 envíos normales a ~2 USD/kg y uno a 40 USD/kg en la misma línea y año
    rows = [rec(netWgt=100000, primaryValue=200000 + i * 1000) for i in range(20)]
    rows.append(rec(netWgt=100000, primaryValue=4_000_000))
    df = flag_unit_value_outliers(parse_comtrade({"data": rows}))
    assert df["is_outlier"].sum() == 1
    assert df.loc[df["is_outlier"], "unit_value_usd_kg"].iloc[0] == 40.0


def test_small_shipments_are_not_flagged():
    """Envíos < 1 t tienen valores unitarios erráticos: no se marcan."""
    rows = [rec(netWgt=100000, primaryValue=200000) for _ in range(20)] + [rec(netWgt=10, primaryValue=5000)]
    df = flag_unit_value_outliers(parse_comtrade({"data": rows}))
    assert df["is_outlier"].sum() == 0


def test_quality_summary_counts():
    df = flag_unit_value_outliers(parse_comtrade({"data": [rec(), rec(partnerCode=724, netWgt=0),
                                                           rec(partnerCode=76, isNetWgtEstimated=True)]}))
    q = quality_summary(df)
    assert q["rows"] == 3 and q["missing_weight"] == 1 and q["estimated_weight"] == 1
