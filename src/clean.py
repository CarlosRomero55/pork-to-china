"""
clean.py · Fase 5 · Limpieza de registros crudos de Comtrade (funciones puras, sin base de datos).

  parse_comtrade(payload)     JSON de Comtrade → DataFrame normalizado
  flag_unit_value_outliers()  marca valores unitarios (USD/kg) atípicos
  quality_summary()           conteos para el reporte de calidad

Al no tocar la base, estas funciones se prueban rápido y por separado.
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

COLUMNS = ["reporter_code", "partner_code", "hs_code", "period", "flow_type",
           "net_weight_kg", "value_usd", "weight_estimated"]


def parse_comtrade(payload: dict) -> pd.DataFrame:
    """
    Normaliza la respuesta de Comtrade:
      - period 'AAAAMM' → fecha (día 1 del mes)
      - solo totales (partner2=0, customs=C00, mot=0); se descarta cualquier desglose
      - netWgt ≤ 0 → NULL (peso desconocido, no "cero toneladas")
      - primaryValue = valor en USD (CIF en importaciones, FOB en exportaciones)
    """
    rows = payload.get("data") or []
    if not rows:
        return pd.DataFrame(columns=COLUMNS)
    df = pd.DataFrame(rows)
    totals = (df.get("partner2Code", 0).fillna(0).astype(int).eq(0)
              & df.get("customsCode", "C00").fillna("C00").eq("C00")
              & df.get("motCode", 0).fillna(0).astype(int).eq(0))
    df = df[totals]
    out = pd.DataFrame({
        "reporter_code": df["reporterCode"].astype(int),
        "partner_code": df["partnerCode"].astype(int),
        "hs_code": df["cmdCode"].astype(str).str.zfill(6),
        "period": [date(int(str(p)[:4]), int(str(p)[4:6]), 1) for p in df["period"]],
        "flow_type": df["flowCode"].astype(str),
        "net_weight_kg": pd.to_numeric(df["netWgt"], errors="coerce"),
        "value_usd": pd.to_numeric(df["primaryValue"], errors="coerce"),
        "weight_estimated": df.get("isNetWgtEstimated", False).fillna(False).astype(bool),
    })
    out.loc[out["net_weight_kg"] <= 0, "net_weight_kg"] = np.nan
    return out.reset_index(drop=True)


def flag_unit_value_outliers(df: pd.DataFrame, k: float = 3.0) -> pd.DataFrame:
    """
    Marca filas con USD/kg atípico DENTRO de su grupo (línea HS × año), usando el rango
    intercuartílico sobre el logaritmo: [Q1 − k·IQR, Q3 + k·IQR].
    El log hace que "el doble" y "la mitad" pesen igual; k=3 solo marca casos extremos.
    No borra nada: agrega unit_value_usd_kg y is_outlier (se decide qué hacer en la Fase 6).
    """
    df = df.copy()
    df["unit_value_usd_kg"] = df["value_usd"] / df["net_weight_kg"]
    df["is_outlier"] = False
    valid = df["unit_value_usd_kg"].gt(0) & df["net_weight_kg"].ge(1000)   # ignora envíos < 1 t
    logs = np.log(df.loc[valid, "unit_value_usd_kg"])
    keys = [df.loc[valid, "hs_code"], pd.to_datetime(df.loc[valid, "period"]).dt.year]
    q1 = logs.groupby(keys).transform(lambda s: s.quantile(0.25))
    q3 = logs.groupby(keys).transform(lambda s: s.quantile(0.75))
    iqr = q3 - q1
    df.loc[valid, "is_outlier"] = (logs < q1 - k * iqr) | (logs > q3 + k * iqr)
    return df


def quality_summary(df: pd.DataFrame) -> dict:
    return {
        "rows": len(df),
        "missing_weight": int(df["net_weight_kg"].isna().sum()),
        "estimated_weight": int(df["weight_estimated"].sum()),
        "outliers": int(df.get("is_outlier", pd.Series(dtype=bool)).sum()),
    }
