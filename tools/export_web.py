"""
export_web.py · Fase 16.3 · Exporta los datos REALES de gold que usa la historia (scrollytelling) del portafolio web.

Salida: web/pork_story.json (se copia al repositorio del portafolio en data/real/pork-historia.json).
Uso:  python -m tools.export_web
"""
from __future__ import annotations

import json
import sys
from datetime import date

import pandas as pd
from sqlalchemy import text

from src import policy_brief as pb
from src.config import ROOT_DIR
from src.db import GOLD, get_engine

OUT = ROOT_DIR / "web" / "pork_story.json"


def build(conn) -> dict:
    f = pb.figures(conn)
    s = pd.read_sql(text(f"SELECT date, observed, is_gap FROM {GOLD}.fact_its_series WHERE model = 'share_value' ORDER BY date"), conn)
    share = [[str(r.date)[:7], None if r.is_gap else round(float(r.observed), 2)] for r in s.itertuples()]
    yearly = pd.read_sql(text(f"""SELECT FLOOR(f.date_key / 10000) AS y, SUM(f.tonnes) AS t, COUNT(DISTINCT FLOOR(f.date_key / 100)) AS m
        FROM {GOLD}.fact_china_imports f JOIN {GOLD}.dim_product p ON p.product_key = f.product_key AND p.hs_code = '020649'
        WHERE f.basis = 'mirror' GROUP BY y ORDER BY y"""), conn)
    offal = [[int(r.y), round(float(r.t)), int(r.m)] for r in yearly.itertuples()]
    bm = pd.read_sql(text(f"SELECT iso3, process_start, market_open, first_export FROM {GOLD}.v_dash_access_benchmark"), conn)
    bench = [{"iso3": r.iso3, "start": None if pd.isna(r.process_start) else int(r.process_start),
              "first_export": None if pd.isna(r.first_export) else int(r.first_export)} for r in bm.itertuples()]
    tr = pd.read_sql(text(f"SELECT trigger_code, role, status, current_value, threshold FROM {GOLD}.fact_trigger ORDER BY sort_order"), conn)
    triggers = [{"code": r.trigger_code, "role": r.role, "status": r.status,
                 "current": None if pd.isna(r.current_value) else round(float(r.current_value), 2),
                 "threshold": None if pd.isna(r.threshold) else round(float(r.threshold), 2)} for r in tr.itertuples()]
    return {
        "as_of": date.today().isoformat(),
        "source": "github.com/CarlosRomero55/pork-to-china (pork_gold)",
        "us_share_value_pct": share,
        "cuts": {"2018": "2018-04", "2020": "2020-02", "2025": "2025-03"},
        "its_pp": {"2018": round(f["its_2018"], 1), "2020": round(f["its_2020"], 1)},
        "us_offal_tonnes_pct": {"before": f["us_offal_before"], "after": f["us_offal_after"]},
        "us_share_last3": round(f["us_share_last3"], 1),
        "china_offal_imports_t": offal,
        "ecuador_reach_t": {"min": round(f["som_min"]), "max": round(f["som_max"])},
        "benchmark": bench,
        "margin_usd_kg": {"fob": round(f["fob_now"], 2), "offal": round(f["offal_now"], 2),
                          "costs": round(f["var_cost"], 2), "margin": round(f["margin_now"], 2)},
        "npv_negative": {"n": f["n_neg"], "of": f["n_scen"]},
        "triggers": triggers,
    }


def main() -> int:
    with get_engine("etl").connect() as conn:
        data = build(conn)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{OUT.relative_to(ROOT_DIR)} · {OUT.stat().st_size / 1024:.1f} KB · {len(data['us_share_value_pct'])} meses")
    return 0


if __name__ == "__main__":
    sys.exit(main())
