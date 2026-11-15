"""
extract_psd.py · Fase 4.3a · USDA FAS PSD (Production, Supply and Distribution) → bronze

Qué descarga (carne de cerdo, todos los países + agregado mundial, 2018 → año actual + 1):
  - Catálogos: productos, países, atributos y unidades (para traducir códigos en silver).
  - Balance por país y año comercial: producción, consumo, importaciones, exportaciones,
    inventarios... (/country/all/year/{año}) y el total mundial (/world/year/{año}).

Diseño:
  - API oficial: https://apps.fas.usda.gov/OpenData · llave de api.data.gov en el encabezado API_KEY.
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
import json
import sys
import time
from collections import Counter
from datetime import date

import requests
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from src.config import DATA_RAW, settings
from src.db import get_engine, save_raw_response, track_batch
from src.logging_setup import get_logger

log = get_logger(__name__)

BASE = "https://apps.fas.usda.gov/OpenData/api/psd"
SOURCE = "usda_psd"
CACHE_DIR = DATA_RAW / "usda_psd"
REFERENCE = ["commodities", "countries", "commodityAttributes", "unitsOfMeasure"]
FALLBACK_PORK_CODE = "0113000"          # Meat, Swine (se usa solo si el catálogo no lo encuentra)
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
    print("Diagnóstico de la API de USDA (1 intento por variante):")
    for label, url, headers in variants:
        try:
            r = session.get(url, timeout=TIMEOUT, headers={**headers, "Accept": "application/json"})
            ctype = r.headers.get("Content-Type", "?").split(";")[0]
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


def run(start_year: int, end_year: int, dry_run: bool = False,
        session: requests.Session | None = None, pause: float = PAUSE_SECONDS) -> dict:
    years = list(range(start_year, end_year + 1))
    n_calls = len(REFERENCE) + 2 * len(years)
    print(f"Plan USDA PSD {start_year}–{end_year}: {n_calls} consultas "
          f"({len(REFERENCE)} catálogos + {len(years)} años × [todos los países, mundo])")
    if dry_run:
        return {"calls": 0}
    api_key = settings.usda_fas_api_key
    if not api_key:
        raise SystemExit("Falta USDA_FAS_API_KEY en .env (se obtiene en https://api.data.gov/signup)")

    session = session or requests.Session()
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
