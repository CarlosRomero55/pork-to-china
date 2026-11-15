"""
validate.py · Fase 6 · Reglas de calidad de datos sobre silver + reporte "antes vs después".

Cada regla devuelve: estado (OK / ALERTA / ERROR), cuántas filas afecta y un detalle.
  - ERROR  = el dato no es confiable → el script termina con código 1 (detiene el pipeline).
  - ALERTA = el dato es usable pero hay que tenerlo en cuenta en el análisis.
El reporte se escribe en docs/data_quality_report.md.

Uso:  python -m src.validate
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date, datetime

import pandas as pd
from sqlalchemy import text

from src.config import ROOT_DIR
from src.db import BRONZE, SILVER, get_engine
from src.clean import MIN_WEIGHT_KG, PLAUSIBLE_USD_KG
from src.harmonize import build_flows
from src.logging_setup import get_logger

log = get_logger(__name__)
REPORT = ROOT_DIR / "docs" / "data_quality_report.md"

MIRROR_WEIGHT_TOLERANCE = 0.10      # ±10% entre lo que dice China y lo que dice el exportador
WORLD_TOLERANCE = 1.01              # la suma de socios no debe superar al total "Mundo" en más de 1%
MISSING_WEIGHT_MAX_SHARE = 0.01     # máx. 1% de filas sin peso


@dataclass
class RuleResult:
    code: str
    name: str
    severity: str        # "error" o "alerta" si falla
    passed: bool
    affected: int
    detail: str

    @property
    def status(self) -> str:
        return "OK" if self.passed else ("ERROR" if self.severity == "error" else "ALERTA")


def _df(conn, sql: str, **params) -> pd.DataFrame:
    return pd.DataFrame(conn.execute(text(sql), params).mappings().all())


def load_silver(conn) -> pd.DataFrame:
    df = _df(conn, f"""
        SELECT f.flow_id, r.comtrade_code AS reporter_code, r.iso3 AS reporter, p.comtrade_code AS partner_code,
               p.iso3 AS partner, f.hs_code, f.period, f.flow_type, f.net_weight_kg, f.value_usd,
               f.quality_flag, s.name AS source
        FROM {SILVER}.trade_flow f
        JOIN {SILVER}.country r ON r.country_id = f.reporter_id
        JOIN {SILVER}.country p ON p.country_id = f.partner_id
        JOIN {SILVER}.source  s ON s.source_id  = f.source_id""")
    for c in ("net_weight_kg", "value_usd"):
        df[c] = pd.to_numeric(df[c])
    df["period"] = pd.to_datetime(df["period"])
    return df


# ---------------------------------------------------------------- reglas
def r01_completeness(df_silver: pd.DataFrame, n_bronze: int, n_quarantine: int) -> RuleResult:
    loaded = len(df_silver)
    ok = loaded + n_quarantine == n_bronze
    return RuleResult("R01", "Completitud bronze → silver", "error", ok, abs(n_bronze - loaded - n_quarantine),
                      f"bronze {es_num(n_bronze)} = silver {es_num(loaded)} + cuarentena {n_quarantine}")


def r02_quarantine(n_quarantine: int) -> RuleResult:
    return RuleResult("R02", "Países fuera del catálogo (cuarentena)", "alerta", n_quarantine == 0,
                      n_quarantine, "todas las filas tienen país conocido" if n_quarantine == 0
                      else "agregar los códigos al catálogo")


def r03_partners_vs_world(df: pd.DataFrame) -> RuleResult:
    d = df[(df["source"] == "comtrade") & (df["reporter"] == "CHN")]
    world = d[d["partner"] == "W00"].groupby(["hs_code", "period"])["net_weight_kg"].sum()
    parts = d[d["partner"] != "W00"].groupby(["hs_code", "period"])["net_weight_kg"].sum()
    j = pd.concat([world.rename("world"), parts.rename("parts")], axis=1).dropna()
    bad = j[j["parts"] > j["world"] * WORLD_TOLERANCE]
    return RuleResult("R03", "Suma de socios ≤ total Mundo (China, peso)", "error", bad.empty, len(bad),
                      f"{len(j)} combinaciones HS×mes revisadas")


def r04_monthly_continuity(df: pd.DataFrame) -> RuleResult:
    gaps = []
    for src, sub in df.groupby("source"):
        months = pd.period_range(sub["period"].min(), sub["period"].max(), freq="M")
        have = set(sub["period"].dt.to_period("M"))
        missing = [str(m) for m in months if m not in have]
        if missing:
            gaps.append(f"{src}: {', '.join(missing[:6])}")
    cover = "; ".join(f"{s}: {g['period'].min():%Y-%m} a {g['period'].max():%Y-%m}" for s, g in df.groupby("source"))
    return RuleResult("R04", "Serie mensual sin huecos", "error", not gaps, len(gaps),
                      " | ".join(gaps) if gaps else cover)


def r05_plausible_unit_value(df: pd.DataFrame) -> tuple[RuleResult, pd.DataFrame]:
    """Toda fila con USD/kg fuera del rango plausible debe estar marcada como atípica."""
    d = df[df["net_weight_kg"] >= MIN_WEIGHT_KG].copy()
    d["usd_kg"] = d["value_usd"] / d["net_weight_kg"]
    d["hs4"] = d["hs_code"].str[:4]
    lo = d["hs4"].map(lambda h: PLAUSIBLE_USD_KG[h][0])
    hi = d["hs4"].map(lambda h: PLAUSIBLE_USD_KG[h][1])
    out = d[(d["usd_kg"] < lo) | (d["usd_kg"] > hi)]
    unflagged = out[~out["quality_flag"].fillna("").str.contains("outlier_unit_value")]
    share = len(out) / max(len(d), 1) * 100
    return (RuleResult("R05", "USD/kg fuera de rango plausible → marcado como atípico", "error",
                       unflagged.empty, len(unflagged),
                       f"{len(out)} filas fuera de rango ({es_num(share, 2)}% de {es_num(len(d))} ≥ 1 t), "
                       f"{len(out) - len(unflagged)} marcadas · carne 0,5–15 · vísceras 0,3–10 · procesado 0,5–100 USD/kg"),
            out)


def r06_missing_weight(df: pd.DataFrame) -> RuleResult:
    n = int(df["net_weight_kg"].isna().sum())
    share = n / max(len(df), 1)
    return RuleResult("R06", f"Filas sin peso ≤ {MISSING_WEIGHT_MAX_SHARE:.0%}", "alerta",
                      share <= MISSING_WEIGHT_MAX_SHARE, n, f"{es_num(share * 100, 3)}% de {es_num(len(df))} filas")


def r07_mirror_reconciliation(df: pd.DataFrame) -> tuple[RuleResult, pd.DataFrame]:
    y = df["period"].dt.year
    direct = df[(df["source"] == "comtrade") & (df["reporter"] == "CHN") & (df["partner"] != "W00") & (y <= 2024)]
    mirror = df[(df["source"] == "comtrade_mirror") & (y <= 2024)]
    d = direct.groupby("partner")["net_weight_kg"].sum()
    m = mirror.groupby("reporter")["net_weight_kg"].sum()
    r = pd.concat([d.rename("china_kg"), m.rename("exportador_kg")], axis=1, join="inner")
    r["ratio"] = r["china_kg"] / r["exportador_kg"]
    big = r[r["china_kg"] > 0.02 * r["china_kg"].sum()]           # exportadores con > 2% del volumen
    bad = big[(big["ratio"] - 1).abs() > MIRROR_WEIGHT_TOLERANCE]
    detail = " · ".join(f"{i} {es_num(v, 3)}" for i, v in big["ratio"].items())
    return (RuleResult("R07", f"Espejo vs directo en peso (±{MIRROR_WEIGHT_TOLERANCE:.0%}, 2018–2024)", "alerta",
                       bad.empty, len(bad), detail), r)


def r08_spikes(df: pd.DataFrame) -> RuleResult:
    """Meses con volumen total > 3× la mediana de su serie (por fuente y grupo HS)."""
    d = df[df["partner"] != "W00"].copy()
    d["hs4"] = d["hs_code"].str[:4]
    s = d.groupby(["source", "hs4", "period"])["net_weight_kg"].sum().reset_index()
    s["median"] = s.groupby(["source", "hs4"])["net_weight_kg"].transform("median")
    bad = s[s["net_weight_kg"] > 3 * s["median"]]
    examples = ", ".join(f"{r.source}/{r.hs4}/{r.period:%Y-%m}" for r in bad.head(4).itertuples())
    return RuleResult("R08", "Picos mensuales > 3× la mediana", "alerta", bad.empty, len(bad),
                      examples or "sin picos extremos")


def r09_no_future(df: pd.DataFrame) -> RuleResult:
    first_of_month = pd.Timestamp(date.today().replace(day=1))
    n = int((df["period"] > first_of_month).sum())
    return RuleResult("R09", "Sin periodos en el futuro", "error", n == 0, n, f"último periodo {df['period'].max():%Y-%m}")


def r10_scd2(conn) -> RuleResult:
    n = conn.execute(text(f"""
        SELECT COUNT(*) FROM {SILVER}.trade_measure a JOIN {SILVER}.trade_measure b
          ON a.imposing_id = b.imposing_id AND a.target_key = b.target_key AND a.hs_code = b.hs_code
         AND a.measure_type = b.measure_type AND a.measure_id < b.measure_id
         AND a.valid_from <= b.valid_to AND b.valid_from <= a.valid_to""")).scalar()
    return RuleResult("R10", "Medidas arancelarias sin vigencias solapadas (SCD2)", "error", n == 0, n,
                      "cada medida tiene una sola tasa vigente por fecha")


def r11_flags_consistent(df: pd.DataFrame) -> RuleResult:
    """La marca missing_weight debe coincidir exactamente con las filas sin peso."""
    flagged = df["quality_flag"].fillna("").str.contains("missing_weight")
    n = int((flagged != df["net_weight_kg"].isna()).sum())
    return RuleResult("R11", "Marcas de calidad coherentes con los datos", "error", n == 0, n,
                      "quality_flag = missing_weight ⇔ peso NULL")


# Interpretación de negocio de cada alerta (se muestra solo si la regla falla)
ALERT_NOTES = {
    "R07": "Un exportador grande con más de 10% de diferencia entre su dato y el de China: revisar tránsito por "
           "terceros países (por ejemplo, Hong Kong) o desfase de fechas antes de usar su espejo.",
    "R08": "Los picos se concentran en 2020–2021: la peste porcina africana redujo la piara china y las "
           "importaciones llegaron a un récord (~4,3 Mt en 2020). Son datos reales, no errores; por eso las "
           "comparaciones de 2025 se hacen contra 2024 y no contra el promedio histórico.",
}

# ---------------------------------------------------------------- reporte

def es_num(v, decimals: int | None = None) -> str:
    """Número en formato español: 5.244.085 y 1,015 (solo números; el texto no se toca)."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return str(v)
    if decimals is None:
        decimals = 0 if isinstance(v, int) or (float(v).is_integer() and abs(v) >= 100) else 3
    txt = f"{v:,.{decimals}f}"
    return txt.replace(",", "_").replace(".", ",").replace("_", ".")


def md_table(df: pd.DataFrame, index: bool = True) -> str:
    """Tabla Markdown sin dependencias extra (pandas.to_markdown exige instalar 'tabulate')."""
    d = df.reset_index() if index else df
    cols = [str(c) for c in d.columns]
    rows = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    rows += ["| " + " | ".join(es_num(v.item() if hasattr(v, "item") else v) for v in r) + " |"
             for r in d.itertuples(index=False)]
    return "\n".join(rows)

def flag_counts(df: pd.DataFrame) -> dict[str, int]:
    f = df["quality_flag"].fillna("")
    return {k: int(f.str.contains(k).sum()) for k in
            ("outlier_unit_value", "missing_weight", "weight_estimated_by_source")} | {"sin_marca": int((f == "").sum())}


def write_report(results, before_after, coverage, recon, implausible, flags) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# Reporte de calidad de datos · Comtrade (bronze → silver)",
        "",
        f"_Generado automáticamente por `src/validate.py` el {now}. No editar a mano._",
        "",
        "## 1. Antes vs después",
        "",
        "| Etapa | Filas |", "|---|---:|",
        *[f"| {k} | {es_num(v)} |" for k, v in before_after.items()],
        "",
        "Ninguna fila se borra: las dudosas se **marcan** en `quality_flag` y gold decide cómo usarlas.",
        "",
        "| Marca en silver | Filas |", "|---|---:|",
        *[f"| `{k}` | {es_num(v)} |" for k, v in flags.items()],
        "",
        "## 2. Reglas de calidad",
        "",
        "| Regla | Descripción | Estado | Filas afectadas | Detalle |", "|---|---|---|---:|---|",
        *[f"| {r.code} | {r.name} | {'✅' if r.passed else ('❌' if r.severity == 'error' else '⚠️')} {r.status} "
          f"| {r.affected} | {r.detail} |" for r in results],
        "",
        *(["### Interpretación de las alertas", ""] +
          [f"- **{r.code} · {r.name}:** {ALERT_NOTES.get(r.code, 'Revisar.')}" for r in results
           if not r.passed and r.severity == "alerta"] + [""]
          if any(not r.passed and r.severity == "alerta" for r in results) else []),
        "### Hallazgos de la revisión de valores unitarios",
        "",
        "- **España, HS 020312 (piernas frescas con hueso), 2018:** 0,27–0,48 USD/kg, imposible para ese producto. "
        "Probable error de clasificación del exportador (huesos o patas declarados como piernas). Marcadas.",
        "- **Reino Unido y Francia, envíos de 1,3–1,9 t a 15–25 USD/kg:** muestras o envíos aéreos, no comercio "
        "representativo. Marcadas.",
        "- La regla estadística (IQR por HS × año) no detectaba los casos de España porque el error se repite "
        "todo el año y se parece a sí mismo; por eso se combina con un rango plausible de negocio.",
        "- Las filas marcadas se excluyen del cálculo de precios promedio en gold, pero sí cuentan en volumen.",
        "",
        "## 3. Cobertura por fuente y año (filas)",
        "",
        md_table(coverage),
        "",
        "## 4. Conciliación espejo vs directo (peso, 2018–2024)",
        "",
        "Ratio = toneladas que China dice haber importado ÷ toneladas que el exportador dice haberle vendido.",
        "",
        (recon.assign(china_t=recon["china_kg"] / 1000, exportador_t=recon["exportador_kg"] / 1000)
         [["china_t", "exportador_t", "ratio"]].sort_values("china_t", ascending=False)
         .round({"china_t": 0, "exportador_t": 0, "ratio": 3}).rename_axis("país"))
         .pipe(md_table),
        "",
        "## 5. Valores unitarios fuera de rango (muestra)",
        "",
        (implausible.sort_values("value_usd", ascending=False).head(10)
         [["source", "reporter", "partner", "hs_code", "period", "net_weight_kg", "usd_kg"]]
         .assign(period=lambda x: x["period"].dt.strftime("%Y-%m"), usd_kg=lambda x: x["usd_kg"].round(2))
         .pipe(md_table, index=False) if len(implausible) else "_Ninguno._"),
        "",
        "## 6. Limitaciones conocidas",
        "",
        "- China no ha publicado en Comtrade sus importaciones mensuales de 2025–2026: ese periodo se cubre con "
        "datos espejo (ADR-008). Los valores espejo son FOB; los de China, CIF (factor de conciliación ≈ 1,037).",
        "- Los 12 exportadores del espejo concentran la gran mayoría del volumen; los demás no aparecen en 2025–2026.",
        "- Comtrade revisa datos con meses de atraso: los 2 últimos años se vuelven a descargar en cada corrida.",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    print("=== Pork to China · Fase 6 · validación de calidad ===\n")
    with get_engine("etl").connect() as conn:
        parsed, quarantine = build_flows(conn)            # lo que bronze dice que debería haber
        n_bronze = len(parsed) + len(quarantine)
        df = load_silver(conn)
        df = df[df["source"].isin(["comtrade", "comtrade_mirror"])]
        scd2 = r10_scd2(conn)

    r05, implausible = r05_plausible_unit_value(df)
    r07, recon = r07_mirror_reconciliation(df)
    results = [r01_completeness(df, n_bronze, len(quarantine)), r02_quarantine(len(quarantine)),
               r03_partners_vs_world(df), r04_monthly_continuity(df), r05, r06_missing_weight(df),
               r07, r08_spikes(df), r09_no_future(df), scd2, r11_flags_consistent(df)]

    print(f"{'Regla':<6}{'Estado':<8}{'Filas':>7}  Descripción · detalle")
    for r in results:
        print(f"{r.code:<6}{r.status:<8}{r.affected:>7}  {r.name} · {r.detail[:110]}")

    flags = flag_counts(df)
    before_after = {"Registros en bronze (última versión de cada consulta)": n_bronze,
                    "Descartados por no ser totales (desgloses)": 0,
                    "En cuarentena (país desconocido)": len(quarantine),
                    "Cargados en silver": len(df),
                    "De ellos, con alguna marca de calidad": len(df) - flags["sin_marca"]}
    coverage = (df.assign(año=df["period"].dt.year).groupby(["año", "source"]).size()
                .unstack(fill_value=0).rename_axis(columns=None))
    write_report(results, before_after, coverage, recon, implausible, flags)

    print("\nMarcas en silver: " + " · ".join(f"{k} {v}" for k, v in flags.items()))
    errors = [r for r in results if not r.passed and r.severity == "error"]
    warns = [r for r in results if not r.passed and r.severity == "alerta"]
    print(f"\nResultado: {len(results) - len(errors) - len(warns)} OK · {len(warns)} alertas · {len(errors)} errores")
    print(f"Reporte: {REPORT.relative_to(ROOT_DIR)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
