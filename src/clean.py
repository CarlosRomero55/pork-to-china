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

# Rango plausible de USD/kg por partida (calibrado con la distribución real 2018–2026).
# Fuera de esto casi siempre hay un error de clasificación o un envío no representativo (muestras).
PLAUSIBLE_USD_KG = {"0203": (0.5, 15.0), "0206": (0.3, 10.0), "0210": (0.5, 100.0)}
MIN_WEIGHT_KG = 1000       # envíos menores a 1 t no se evalúan (valores unitarios erráticos)

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
    Marca filas con USD/kg atípico si se cumple CUALQUIERA de dos criterios:
      1. Estadístico: fuera de [Q1 − k·IQR, Q3 + k·IQR] sobre el logaritmo, dentro de su grupo
         (línea HS × año). El log hace que "el doble" y "la mitad" pesen igual; k=3 = solo extremos.
      2. De negocio: fuera del rango plausible de su partida (PLAUSIBLE_USD_KG). Atrapa errores
         sistemáticos que el criterio 1 no ve porque se repiten todo el año (p. ej. una mala
         clasificación que se parece a sí misma).
    No borra nada: agrega unit_value_usd_kg y is_outlier.
    """
    df = df.copy()
    df["unit_value_usd_kg"] = df["value_usd"] / df["net_weight_kg"]
    df["is_outlier"] = False
    valid = df["unit_value_usd_kg"].gt(0) & df["net_weight_kg"].ge(MIN_WEIGHT_KG)
    logs = np.log(df.loc[valid, "unit_value_usd_kg"])
    keys = [df.loc[valid, "hs_code"], pd.to_datetime(df.loc[valid, "period"]).dt.year]
    q1 = logs.groupby(keys).transform(lambda s: s.quantile(0.25))
    q3 = logs.groupby(keys).transform(lambda s: s.quantile(0.75))
    iqr = q3 - q1
    df.loc[valid, "is_outlier"] = (logs < q1 - k * iqr) | (logs > q3 + k * iqr)

    hs4 = df.loc[valid, "hs_code"].str[:4]
    lo = hs4.map(lambda h: PLAUSIBLE_USD_KG.get(h, (0, float("inf")))[0])
    hi = hs4.map(lambda h: PLAUSIBLE_USD_KG.get(h, (0, float("inf")))[1])
    uv = df.loc[valid, "unit_value_usd_kg"]
    df.loc[valid, "is_outlier"] = df.loc[valid, "is_outlier"] | (uv < lo) | (uv > hi)
    return df


def quality_summary(df: pd.DataFrame) -> dict:
    return {
        "rows": len(df),
        "missing_weight": int(df["net_weight_kg"].isna().sum()),
        "estimated_weight": int(df["weight_estimated"].sum()),
        "outliers": int(df.get("is_outlier", pd.Series(dtype=bool)).sum()),
    }
