"""
extract_comtrade.py · Fase 4 · UN Comtrade → bronze

Descarga el comercio MENSUAL de cerdo (12 líneas HS) para:
  - importaciones de China   (reporter 156, flujo M), todos los países socios
  - exportaciones de Ecuador (reporter 218, flujo X), todos los países socios
desde START_YEAR (2018) hasta el año actual.

Diseño:
  - 1 consulta por reporter × flujo × año (12 meses + 12 líneas HS en una sola llamada).
  - Solo totales: partner2Code=0, customsCode=C00, motCode=0 (evita filas desagregadas duplicadas).
  - Caché en data/raw/comtrade/*.json: los años "cerrados" (anteriores a la ventana de
    revisión) no se vuelven a pedir. Los 2 últimos años siempre se piden de nuevo, porque
    los países corrigen y completan sus reportes con meses de atraso.
  - Reintentos con espera exponencial ante 429 (límite de la API) y errores 5xx.
  - Cada respuesta se guarda intacta en pork_bronze.raw_api_response (sin duplicar, por hash)
    y cada ejecución queda registrada en pork_bronze.extract_batch.

Uso:
  python -m src.extract_comtrade --dry-run     # muestra el plan, no llama a la API
  python -m src.extract_comtrade               # extracción incremental
  python -m src.extract_comtrade --refresh     # vuelve a pedir todos los años
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import requests
from tenacity import (retry, retry_if_exception, stop_after_attempt,
                      wait_exponential)

from src.config import DATA_RAW, settings
from src.db import get_engine, save_raw_response, track_batch
from src.logging_setup import get_logger

log = get_logger(__name__)

BASE_URL = "https://comtradeapi.un.org/data/v1/get/C/M/HS"   # C = bienes, M = mensual, HS
SOURCE = "comtrade"
CACHE_DIR = DATA_RAW / "comtrade"
HS_CODES = ["020311", "020312", "020319", "020321", "020322", "020329",
            "020630", "020641", "020649", "021011", "021012", "021019"]
REVISION_WINDOW_YEARS = 2      # los 2 últimos años siempre se vuelven a pedir
PAUSE_SECONDS = 1.5            # pausa entre llamadas (cortesía con el límite de la API)
TIMEOUT = (10, 120)            # conexión, lectura


@dataclass(frozen=True)
class Query:
    reporter_code: int
    reporter_iso3: str
    flow: str          # "M" importación, "X" exportación
    year: int

    @property
    def cache_file(self) -> Path:
        return CACHE_DIR / f"{self.reporter_iso3}_{self.flow}_{self.year}.json"

    def params(self) -> dict:
        return {
            "reporterCode": self.reporter_code,
            "period": ",".join(f"{self.year}{m:02d}" for m in range(1, 13)),
            "cmdCode": ",".join(HS_CODES),
            "flowCode": self.flow,
            "partner2Code": 0,
            "customsCode": "C00",
            "motCode": 0,
            "maxRecords": 100000,
            "includeDesc": "false",
        }


QUERY_SPECS = [(156, "CHN", "M"), (218, "ECU", "X")]


def build_plan(start_year: int, end_year: int, refresh: bool = False) -> tuple[list[Query], list[Query]]:
    """Devuelve (consultas a la API, consultas servidas desde caché)."""
    to_fetch, from_cache = [], []
    closed_until = end_year - REVISION_WINDOW_YEARS
    for code, iso3, flow in QUERY_SPECS:
        for year in range(start_year, end_year + 1):
            q = Query(code, iso3, flow, year)
            if not refresh and year <= closed_until and q.cache_file.exists():
                from_cache.append(q)
            else:
                to_fetch.append(q)
    return to_fetch, from_cache


# ---------------------------------------------------------------- HTTP con reintentos
class RetryableHTTPError(Exception):
    """Error temporal (429 o 5xx): vale la pena reintentar."""


def _is_retryable(exc: BaseException) -> bool:
    return isinstance(exc, (RetryableHTTPError, requests.ConnectionError, requests.Timeout))


@retry(retry=retry_if_exception(_is_retryable), stop=stop_after_attempt(5),
       wait=wait_exponential(multiplier=2, min=2, max=60), reraise=True)
def fetch(session: requests.Session, query: Query, api_key: str) -> dict:
    """Llama a la API. Reintenta hasta 5 veces con espera 2s, 4s, 8s... ante errores temporales."""
    resp = session.get(BASE_URL, params=query.params(), timeout=TIMEOUT,
                       headers={"Ocp-Apim-Subscription-Key": api_key})
    if resp.status_code == 429 or resp.status_code >= 500:
        wait = resp.headers.get("Retry-After")
        log.warning("HTTP %s en %s %s %s (Retry-After=%s); se reintenta",
                    resp.status_code, query.reporter_iso3, query.flow, query.year, wait)
        if wait and wait.isdigit():
            time.sleep(min(int(wait), 60))
        raise RetryableHTTPError(f"HTTP {resp.status_code}")
    if resp.status_code in (401, 403):
        raise PermissionError("Comtrade rechazó la llave (401/403). Revisa COMTRADE_API_KEY en .env")
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("error"):
        raise RuntimeError(f"Comtrade devolvió error: {payload['error']}")
    return payload


def summarize(records: list[dict]) -> str:
    """Resumen legible: meses con datos y los 5 socios con más registros."""
    months = sorted({str(r.get("period")) for r in records})
    partners = Counter(r.get("partnerCode") for r in records if r.get("partnerCode") != 0)
    top = ", ".join(str(p) for p, _ in partners.most_common(5))
    span = f"{months[0]}–{months[-1]}" if months else "sin datos"
    return f"{len(records):>5} registros · meses {span} ({len(months)}) · socios top (código): {top}"


# ---------------------------------------------------------------- ejecución
def run(start_year: int, end_year: int, refresh: bool = False, dry_run: bool = False,
        session: requests.Session | None = None, pause: float = PAUSE_SECONDS) -> dict:
    to_fetch, from_cache = build_plan(start_year, end_year, refresh)
    print(f"Plan Comtrade {start_year}–{end_year}: {len(to_fetch)} consultas a la API · "
          f"{len(from_cache)} años servidos desde caché")
    print(f"  Cupo diario gratuito: 500 consultas → este plan usa {len(to_fetch)}")
    if dry_run:
        for q in to_fetch:
            print(f"  · API   {q.reporter_iso3} {'importaciones' if q.flow == 'M' else 'exportaciones'} {q.year}")
        for q in from_cache:
            print(f"  · caché {q.reporter_iso3} {q.flow} {q.year}")
        return {"fetched": 0, "cached": len(from_cache), "new_raw": 0, "records": 0}

    api_key = settings.comtrade_api_key
    if not api_key:
        raise SystemExit("Falta COMTRADE_API_KEY en .env (ver comtradedeveloper.un.org/profile)")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    session = session or requests.Session()
    stats = {"fetched": 0, "cached": len(from_cache), "new_raw": 0, "records": 0}
    engine = get_engine("etl")

    with track_batch(SOURCE, {"start_year": start_year, "end_year": end_year,
                              "refresh": refresh, "hs": HS_CODES}) as batch:
        jobs = [(q, None) for q in from_cache] + [(q, "api") for q in to_fetch]
        for i, (q, origin) in enumerate(jobs, 1):
            if origin == "api":
                payload = fetch(session, q, api_key)
                q.cache_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
                stats["fetched"] += 1
                if pause:
                    time.sleep(pause)
            else:
                payload = json.loads(q.cache_file.read_text(encoding="utf-8"))
            records = payload.get("data") or []
            with engine.begin() as conn:
                _, is_new = save_raw_response(conn, batch.batch_id, SOURCE, BASE_URL, q.params(), payload)
            stats["new_raw"] += int(is_new)
            stats["records"] += len(records)
            batch.rows_loaded += len(records) if is_new else 0
            tag = "nuevo " if is_new else "igual "
            print(f"  [{i:>2}/{len(jobs)}] {q.reporter_iso3} {q.flow} {q.year} · "
                  f"{'API  ' if origin else 'caché'} · {tag}· {summarize(records)}")
    print(f"\nResumen: {stats['fetched']} llamadas a la API · {stats['new_raw']} respuestas nuevas en bronze · "
          f"{stats['records']} registros en total")
    return stats


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Extrae comercio de cerdo de UN Comtrade a bronze")
    p.add_argument("--start-year", type=int, default=settings.start_year)
    p.add_argument("--end-year", type=int, default=date.today().year)
    p.add_argument("--refresh", action="store_true", help="ignora la caché y pide todo de nuevo")
    p.add_argument("--dry-run", action="store_true", help="solo muestra el plan")
    a = p.parse_args(argv)
    print("=== Pork to China · Fase 4 · extracción UN Comtrade ===\n")
    run(a.start_year, a.end_year, refresh=a.refresh, dry_run=a.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
