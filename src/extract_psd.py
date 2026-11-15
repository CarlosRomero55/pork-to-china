"""
extract_psd.py · Fase 4.3a · USDA FAS PSD (Production, Supply and Distribution) → bronze

Qué descarga (carne de cerdo, todos los países + agregado mundial, 2018 → año actual + 1):
  - Catálogos: productos, países, atributos y unidades (para traducir códigos en silver).
  - Balance por país y año comercial: producción, consumo, importaciones, exportaciones,
    inventarios... (/country/all/year/{año}) y el total mundial (/world/year/{año}).

Dos vías (se elige sola):
  1. API oficial: https://apps.fas.usda.gov/OpenData · llave de api.data.gov en el encabezado API_KEY.
  2. Plan B, DESCARGA MASIVA de PSD Online (psd_livestock_csv.zip): se usa si la API no responde
     (en nov-2026 devolvía HTTP 500 en todas las rutas con la llave aceptada). No necesita llave.

Diseño:
  - El código del producto NO se escribe a mano: se busca en el catálogo (nombre con "swine"/"pork").
  - Solo guarda respuestas crudas en bronze (hash anti-duplicados) y en data/raw/usda_psd/.
    La interpretación de campos va en el paso siguiente, con la estructura real a la vista.
  - Al final imprime un REPORTE DE DESCUBRIMIENTO: campos de cada registro, atributos de China, etc.
  - Reintentos con espera exponencial ante 429/5xx; 401/403 falla de inmediato.

Uso:
  python -m src.extract_psd --dry-run
  python -m src.extract_psd
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import zipfile
import sys
import time
from collections import Counter
from datetime import date

import pandas as pd

import requests
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from src.config import DATA_RAW, ROOT_DIR, settings
from src.db import BRONZE, get_engine, save_raw_response, track_batch
from src.logging_setup import get_logger

log = get_logger(__name__)

BASE = "https://apps.fas.usda.gov/OpenData/api/psd"
SOURCE = "usda_psd"
CACHE_DIR = DATA_RAW / "usda_psd"
REFERENCE = ["commodities", "countries", "commodityAttributes", "unitsOfMeasure"]
FALLBACK_PORK_CODE = "0113000"          # Meat, Swine (se usa solo si el catálogo no lo encuentra)
BULK_URLS = [   # se prueban en orden
    "https://apps.fas.usda.gov/psdonline/downloads/psd_livestock_csv.zip",
    "https://apps.fas.usda.gov/psdonline/downloads/psd_alldata_csv.zip",
]
PAUSE_SECONDS = 0.5
TIMEOUT = (10, 120)


class RetryableHTTPError(Exception):
    pass


def _is_retryable(exc: BaseException) -> bool:
    return isinstance(exc, (RetryableHTTPError, requests.ConnectionError, requests.Timeout))


@retry(retry=retry_if_exception(_is_retryable), stop=stop_after_attempt(5),
       wait=wait_exponential(multiplier=2, min=2, max=60), reraise=True)
def get_json(session: requests.Session, path: str, api_key: str):
    resp = session.get(f"{BASE}/{path}", timeout=TIMEOUT, headers={"API_KEY": api_key, "Accept": "application/json"})
    if resp.status_code == 429 or resp.status_code >= 500:
        log.warning("HTTP %s en %s; se reintenta · respuesta: %s", resp.status_code, path, _snippet(resp))
        raise RetryableHTTPError(f"HTTP {resp.status_code} en {path}: {_snippet(resp)}")
    if resp.status_code in (401, 403):
        raise PermissionError("USDA rechazó la llave (401/403). Revisa USDA_FAS_API_KEY en .env")
    resp.raise_for_status()
    return resp.json()


def _snippet(resp, n: int = 200) -> str:
    """Primeros caracteres del cuerpo de la respuesta (para diagnosticar errores del servidor)."""
    try:
        return " ".join(str(resp.text).split())[:n]
    except Exception:
        return "(sin cuerpo)"


def probe(session: requests.Session, api_key: str) -> None:
    """Diagnóstico: prueba variantes UNA vez cada una y muestra código + mensaje. No guarda nada."""
    year = date.today().year - 1
    variants = [
        ("catálogo commodities, llave en encabezado", f"{BASE}/commodities", {"API_KEY": api_key}),
        ("catálogo countries, llave en encabezado", f"{BASE}/countries", {"API_KEY": api_key}),
        (f"datos cerdo {year}, llave en encabezado", f"{BASE}/commodity/{FALLBACK_PORK_CODE}/country/all/year/{year}",
         {"API_KEY": api_key}),
        (f"datos cerdo {year}, llave como parámetro", f"{BASE}/commodity/{FALLBACK_PORK_CODE}/country/all/year/{year}"
         f"?api_key={api_key}", {}),
        ("catálogo commodities, SIN llave (debe dar 401/403)", f"{BASE}/commodities", {}),
    ]
    variants += [(f"descarga masiva {u.rsplit('/', 1)[1]}", u, {}) for u in BULK_URLS]
    print("Diagnóstico de USDA (1 intento por variante):")
    for label, url, headers in variants:
        try:
            r = session.get(url, timeout=TIMEOUT, headers={**headers, "Accept": "application/json"})
            ctype = r.headers.get("Content-Type", "?").split(";")[0]
            if ctype in ("application/zip", "application/x-zip-compressed", "application/octet-stream"):
                body = f"archivo ZIP de {len(r.content) / 1e6:.1f} MB disponible"
            else:
                body = _snippet(r).replace(api_key, "***") if api_key else _snippet(r)
            print(f"  [{r.status_code}] {label} · {ctype} · {body[:160]}")
        except requests.RequestException as e:
            print(f"  [ERR] {label} · {type(e).__name__}: {e}")


def _norm(record: dict) -> dict:
    """Claves en minúscula y sin guiones bajos: 'commodityCode', 'CommodityCode' y 'commodity_code' coinciden."""
    return {k.lower().replace("_", ""): v for k, v in record.items()}


def find_pork_code(commodities: list[dict]) -> tuple[str, str]:
    """Busca en el catálogo el código de la carne de cerdo (ej. 'Meat, Swine')."""
    for raw in commodities or []:
        r = _norm(raw)
        name = str(r.get("commodityname") or r.get("name") or "")
        code = str(r.get("commoditycode") or r.get("code") or "")
        low = name.lower()
        if ("swine" in low or "pork" in low) and "meat" in low:
            return code, name
    return FALLBACK_PORK_CODE, "Meat, Swine (código por defecto: no se halló en el catálogo)"


def save(engine, batch_id: int, path: str, payload) -> bool:
    fname = path.replace("/", "_") + ".json"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / fname).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with engine.begin() as conn:
        _, is_new = save_raw_response(conn, batch_id, SOURCE, f"{BASE}/{path}", {"path": path},
                                      payload if isinstance(payload, dict) else {"data": payload})
    return is_new


def discovery_report(pork: tuple[str, str], data_by_year: dict[int, list], countries: list[dict],
                     attributes: list[dict]) -> None:
    """Muestra la estructura REAL de la respuesta para diseñar la transformación sin suposiciones."""
    print("\n=== Reporte de descubrimiento (estructura real de la API) ===")
    print(f"Producto: {pork[1]} · código {pork[0]}")
    sample = next((recs[0] for recs in data_by_year.values() if recs), None)
    if sample is None:
        print("Ningún año devolvió registros: revisar el código del producto.")
        return
    print(f"Campos de cada registro: {list(sample.keys())}")
    print(f"Ejemplo: {json.dumps(sample, ensure_ascii=False)[:300]}")
    print("Registros por año: " + " · ".join(f"{y}: {len(r)}" for y, r in sorted(data_by_year.items())))

    names = {}
    for c in countries or []:
        n = _norm(c)
        names[str(n.get("countrycode") or n.get("code"))] = n.get("countryname") or n.get("name")
    attr_names = {}
    for a in attributes or []:
        n = _norm(a)
        attr_names[str(n.get("attributeid") or n.get("id"))] = n.get("attributename") or n.get("name")

    recs = [_norm(r) for rs in data_by_year.values() for r in rs]
    by_country = Counter(str(r.get("countrycode")) for r in recs)
    print(f"Países con datos de cerdo: {len(by_country)} → " +
          ", ".join(f"{c} ({names.get(c, '?')})" for c, _ in by_country.most_common(12)))
    china = [r for r in recs if "china" in str(names.get(str(r.get("countrycode")), "")).lower()]
    if china:
        attrs = sorted({attr_names.get(str(r.get("attributeid")), str(r.get("attributeid"))) for r in china})
        print(f"Atributos disponibles para China: {attrs}")
        last = max(int(r.get("marketyear", 0)) for r in china)
        prod = [r for r in china if int(r.get("marketyear", 0)) == last
                and "production" in str(attr_names.get(str(r.get("attributeid")), "")).lower()]
        if prod:
            print(f"China · producción {last}: {prod[0].get('value')} (unidad id {prod[0].get('unitid')})")


# ---------------------------------------------------------------- vía 2: descarga masiva
def api_healthcheck(session: requests.Session, api_key: str) -> bool:
    """Una sola llamada, sin reintentos: ¿la API responde datos ahora mismo?"""
    if not api_key:
        return False
    url = f"{BASE}/commodity/{FALLBACK_PORK_CODE}/world/year/{date.today().year - 1}"
    try:
        r = session.get(url, timeout=TIMEOUT, headers={"API_KEY": api_key, "Accept": "application/json"})
        return r.status_code == 200
    except requests.RequestException:
        return False


def download_bulk(session: requests.Session) -> tuple[str, bytes]:
    """Descarga el primer ZIP disponible de PSD Online. Devuelve (url, contenido)."""
    errors = []
    for url in BULK_URLS:
        try:
            r = session.get(url, timeout=(10, 300), headers={"Accept": "application/zip"})
            if r.status_code == 200 and r.content[:2] == b"PK":      # firma de un ZIP
                return url, r.content
            errors.append(f"{url.rsplit('/', 1)[1]} → HTTP {r.status_code}")
        except requests.RequestException as e:
            errors.append(f"{url.rsplit('/', 1)[1]} → {type(e).__name__}")
    raise RuntimeError("No se pudo descargar PSD Online: " + "; ".join(errors))


def read_pork_from_zip(content: bytes) -> pd.DataFrame:
    """Lee el CSV del ZIP y deja solo la carne de cerdo. Columnas normalizadas (minúsculas, sin '_')."""
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        with z.open(name) as f:
            df = pd.read_csv(f, dtype=str, encoding="utf-8-sig")
    df.columns = [c.lower().replace("_", "").replace(" ", "") for c in df.columns]
    desc = df.get("commoditydescription", pd.Series("", index=df.index)).str.lower()
    is_pork = (desc.str.contains("swine") | desc.str.contains("pork")) & desc.str.contains("meat")
    if "commoditycode" in df.columns:
        is_pork |= df["commoditycode"].eq(FALLBACK_PORK_CODE)
    return df[is_pork].reset_index(drop=True)


def _rel(path) -> str:
    """Ruta relativa a la raíz del proyecto (o absoluta si está fuera, p. ej. en pruebas)."""
    try:
        return str(path.relative_to(ROOT_DIR)).replace("\\", "/")
    except ValueError:
        return str(path)


def register_file(engine, batch_id: int, url: str, content: bytes) -> tuple[str, bool]:
    """Guarda el ZIP en data/raw/usda_psd y lo registra en bronze.raw_file (sin duplicar por hash)."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fname = url.rsplit("/", 1)[1]
    path = CACHE_DIR / fname
    path.write_bytes(content)
    digest = hashlib.sha256(content).hexdigest()
    from sqlalchemy import text
    with engine.begin() as conn:
        res = conn.execute(text(f"""INSERT IGNORE INTO {BRONZE}.raw_file
            (batch_id, source_name, file_name, stored_path, source_url, file_hash)
            VALUES (:b, :s, :f, :p, :u, :h)"""),
            {"b": batch_id, "s": SOURCE, "f": fname, "p": _rel(path),
             "u": url, "h": digest})
    return digest, res.rowcount == 1


def bulk_discovery(df: pd.DataFrame, start_year: int) -> None:
    print("\n=== Reporte de descubrimiento (descarga masiva, estructura real) ===")
    if df.empty:
        print("El archivo no trae registros de carne de cerdo: revisar el contenido del ZIP.")
        return
    print(f"Columnas: {list(df.columns)}")
    print(f"Producto: {df['commoditydescription'].iloc[0]} · código {df['commoditycode'].iloc[0]}")
    years = pd.to_numeric(df["marketyear"], errors="coerce")
    print(f"Registros de cerdo: {len(df)} · años {int(years.min())}–{int(years.max())} · "
          f"desde {start_year}: {(years >= start_year).sum()}")
    countries = df.drop_duplicates("countrycode")[["countrycode", "countryname"]]
    print(f"Países con datos: {len(countries)} → " + ", ".join(
        f"{r.countrycode} ({r.countryname})" for r in countries.head(14).itertuples()))
    ch = df[df["countryname"].str.lower().eq("china")]
    if len(ch):
        print(f"Atributos de China: {sorted(ch['attributedescription'].unique())}")
        unit = ch["unitdescription"].iloc[0] if "unitdescription" in ch else "?"
        last = ch[pd.to_numeric(ch["marketyear"]) >= start_year]
        piv = (last[last["attributedescription"].isin(["Production", "Imports", "Domestic Consumption"])]
               .assign(v=lambda x: pd.to_numeric(x["value"], errors="coerce"))
               .pivot_table(index="marketyear", columns="attributedescription", values="v", aggfunc="last"))
        if len(piv):
            print(f"China (unidad: {unit}):\n" + piv.to_string())


def run_bulk(session: requests.Session, start_year: int) -> dict:
    print("  → La API no responde; se usa la DESCARGA MASIVA de PSD Online (no necesita llave)")
    engine = get_engine("etl")
    with track_batch(SOURCE, {"mode": "bulk", "start_year": start_year, "urls": BULK_URLS}) as batch:
        url, content = download_bulk(session)
        digest, is_new = register_file(engine, batch.batch_id, url, content)
        df = read_pork_from_zip(content)
        batch.rows_loaded = len(df) if is_new else 0
        print(f"  {url.rsplit('/', 1)[1]} · {len(content) / 1e6:.1f} MB · "
              f"{'nuevo' if is_new else 'igual (mismo archivo que la última vez)'} · {len(df)} registros de cerdo")
    bulk_discovery(df, start_year)
    return {"mode": "bulk", "calls": 1, "new_raw": int(is_new), "records": len(df)}


def run(start_year: int, end_year: int, dry_run: bool = False,
        session: requests.Session | None = None, pause: float = PAUSE_SECONDS) -> dict:
    years = list(range(start_year, end_year + 1))
    n_calls = len(REFERENCE) + 2 * len(years)
    print(f"Plan USDA PSD {start_year}–{end_year}: {n_calls} consultas "
          f"({len(REFERENCE)} catálogos + {len(years)} años × [todos los países, mundo])")
    if dry_run:
        return {"calls": 0}
    api_key = settings.usda_fas_api_key
    session = session or requests.Session()
    if not api_healthcheck(session, api_key):
        return run_bulk(session, start_year)
    print("  → La API responde: se usa la API")
    engine = get_engine("etl")
    stats = {"calls": 0, "new_raw": 0, "records": 0}
    refs: dict[str, list] = {}
    data_by_year: dict[int, list] = {}

    with track_batch(SOURCE, {"start_year": start_year, "end_year": end_year}) as batch:
        for name in REFERENCE:
            # Los catálogos solo traducen códigos: si fallan, se sigue con los datos (lo importante)
            try:
                payload = get_json(session, name, api_key)
            except RetryableHTTPError as e:
                log.warning("Catálogo %s no disponible (%s); se continúa sin él", name, e)
                print(f"  catálogo {name:<20} NO DISPONIBLE (se continúa)")
                refs[name] = []
                stats.setdefault("missing_refs", []).append(name)
                continue
            refs[name] = payload if isinstance(payload, list) else payload.get("data", [])
            stats["new_raw"] += save(engine, batch.batch_id, name, payload)
            stats["calls"] += 1
            print(f"  catálogo {name:<20} {len(refs[name]):>5} elementos")
            time.sleep(pause)

        pork = find_pork_code(refs["commodities"])
        print(f"  producto cerdo → {pork[1]} (código {pork[0]})")
        for y in years:
            for scope in ("country/all", "world"):
                path = f"commodity/{pork[0]}/{scope}/year/{y}"
                payload = get_json(session, path, api_key)
                records = payload if isinstance(payload, list) else payload.get("data", [])
                if scope == "country/all":
                    data_by_year[y] = records
                is_new = save(engine, batch.batch_id, path, payload)
                stats["new_raw"] += is_new
                stats["records"] += len(records)
                stats["calls"] += 1
                batch.rows_loaded += len(records) if is_new else 0
                print(f"  {y} {scope:<12} {len(records):>5} registros · {'nuevo' if is_new else 'igual'}")
                time.sleep(pause)

    discovery_report(pork, data_by_year, refs.get("countries"), refs.get("commodityAttributes"))
    print(f"\nResumen: {stats['calls']} llamadas · {stats['new_raw']} respuestas nuevas en bronze · "
          f"{stats['records']} registros")
    return stats


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Extrae el balance de cerdo de USDA PSD a bronze")
    p.add_argument("--start-year", type=int, default=settings.start_year)
    p.add_argument("--end-year", type=int, default=date.today().year + 1, help="incluye la proyección")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--probe", action="store_true", help="diagnóstico de la API, no guarda nada")
    a = p.parse_args(argv)
    print("=== Pork to China · Fase 4.3a · extracción USDA PSD ===\n")
    if a.probe:
        if not settings.usda_fas_api_key:
            raise SystemExit("Falta USDA_FAS_API_KEY en .env")
        probe(requests.Session(), settings.usda_fas_api_key)
        return 0
    run(a.start_year, a.end_year, dry_run=a.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
