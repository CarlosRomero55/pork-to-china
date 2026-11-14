"""
extract_comtrade.py · Fase 4 · UN Comtrade → bronze

Descarga el comercio MENSUAL de cerdo (12 líneas HS), desde START_YEAR (2018):

  1. DIRECTO · lo que reporta cada país:
       - importaciones de China   (reporter 156, flujo M), todos los socios
       - exportaciones de Ecuador (reporter 218, flujo X), todos los socios
  2. ESPEJO (mirror) · lo que los 12 principales exportadores dicen haberle vendido a China
       (reporters = exportadores, partner = 156, flujo X). Cubre los meses que China
       todavía no reporta a Comtrade. Valores FOB (los de China son CIF): se concilian en la Fase 5.
  3. DISPONIBILIDAD · consulta getDa de Comtrade para saber qué meses ha publicado
       cada reporter (diagnóstico de huecos; no gasta datos).

Diseño:
  - 1 consulta por grupo × año (12 meses + 12 HS + varios reporters en una sola llamada).
  - Solo totales: partner2Code=0, customsCode=C00, motCode=0 (evita duplicar volúmenes).
  - Caché en data/raw/comtrade/*.json: los años "cerrados" (fuera de la ventana de
    revisión de 2 años) no se vuelven a pedir.
  - Reintentos con espera exponencial ante 429/5xx; 401/403 falla de inmediato.
  - Cada respuesta se guarda intacta en pork_bronze.raw_api_response (sin duplicar, por hash)
    y cada ejecución queda registrada en pork_bronze.extract_batch.

Uso:
  python -m src.extract_comtrade --dry-run     # muestra el plan, no llama a la API
  python -m src.extract_comtrade               # extracción incremental (directo + espejo + disponibilidad)
  python -m src.extract_comtrade --refresh     # vuelve a pedir todos los años
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
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

BASE_URL = "https://comtradeapi.un.org/data/v1/get/C/M/HS"       # C = bienes, M = mensual, HS
DA_URL = "https://comtradeapi.un.org/data/v1/getDa/C/M/HS"       # disponibilidad de datos
SOURCE = "comtrade"
CACHE_DIR = DATA_RAW / "comtrade"
HS_CODES = ["020311", "020312", "020319", "020321", "020322", "020329",
            "020630", "020641", "020649", "021011", "021012", "021019"]
REVISION_WINDOW_YEARS = 2      # los 2 últimos años siempre se vuelven a pedir
PAUSE_SECONDS = 1.5            # pausa entre llamadas (cortesía con el límite de la API)
TIMEOUT = (10, 120)            # conexión, lectura

# Principales exportadores de cerdo a China (2018–2024, según los datos directos) + otros relevantes
MIRROR_REPORTERS = {724: "ESP", 842: "USA", 76: "BRA", 124: "CAN", 152: "CHL", 208: "DNK",
                    528: "NLD", 276: "DEU", 251: "FRA", 826: "GBR", 372: "IRL", 616: "POL"}
CHINA = 156

# (etiqueta, reporters, flujo, partner) · partner None = todos los socios
QUERY_GROUPS = [
    ("CHN", [156], "M", None),                          # directo: importaciones de China
    ("ECU", [218], "X", None),                          # directo: exportaciones de Ecuador
    ("MIRROR", list(MIRROR_REPORTERS), "X", CHINA),     # espejo: exportaciones hacia China
]


@dataclass(frozen=True)
class Query:
    label: str
    reporters: tuple[int, ...]
    flow: str          # "M" importación, "X" exportación
    partner: int | None
    year: int

    @property
    def is_mirror(self) -> bool:
        return self.partner is not None

    @property
    def cache_file(self) -> Path:
        return CACHE_DIR / f"{self.label}_{self.flow}_{self.year}.json"

    def params(self) -> dict:
        p = {
            "reporterCode": ",".join(str(r) for r in self.reporters),
            "period": ",".join(f"{self.year}{m:02d}" for m in range(1, 13)),
            "cmdCode": ",".join(HS_CODES),
            "flowCode": self.flow,
            "partner2Code": 0,
            "customsCode": "C00",
            "motCode": 0,
            "maxRecords": 100000,
            "includeDesc": "false",
        }
        if self.partner is not None:
            p["partnerCode"] = self.partner
        return p


def build_plan(start_year: int, end_year: int, refresh: bool = False) -> tuple[list[Query], list[Query]]:
    """Devuelve (consultas a la API, consultas servidas desde caché)."""
    to_fetch, from_cache = [], []
    closed_until = end_year - REVISION_WINDOW_YEARS
    for label, reporters, flow, partner in QUERY_GROUPS:
        for year in range(start_year, end_year + 1):
            q = Query(label, tuple(reporters), flow, partner, year)
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
def _get(session: requests.Session, url: str, params: dict, api_key: str, what: str) -> dict:
    """GET a Comtrade. Reintenta hasta 5 veces (2s, 4s, 8s...) ante errores temporales."""
    resp = session.get(url, params=params, timeout=TIMEOUT,
                       headers={"Ocp-Apim-Subscription-Key": api_key})
    if resp.status_code == 429 or resp.status_code >= 500:
        wait = resp.headers.get("Retry-After")
        log.warning("HTTP %s en %s (Retry-After=%s); se reintenta", resp.status_code, what, wait)
        if wait and wait.isdigit():
            time.sleep(min(int(wait), 60))
        raise RetryableHTTPError(f"HTTP {resp.status_code}")
    if resp.status_code in (401, 403):
        raise PermissionError("Comtrade rechazó la llave (401/403). Revisa COMTRADE_API_KEY en .env")
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("error"):
        raise RuntimeError(f"Comtrade devolvió error en {what}: {payload['error']}")
    return payload


def fetch(session: requests.Session, query: Query, api_key: str) -> dict:
    return _get(session, BASE_URL, query.params(), api_key, f"{query.label} {query.flow} {query.year}")


# Se expone el objeto de reintentos para que las pruebas puedan anular las esperas
fetch.retry = _get.retry  # type: ignore[attr-defined]


def summarize(query: Query, records: list[dict]) -> str:
    """Resumen legible: meses con datos y los 5 países con más registros."""
    months = sorted({str(r.get("period")) for r in records})
    key = "reporterCode" if query.is_mirror else "partnerCode"
    who = Counter(r.get(key) for r in records if r.get(key) != 0)
    label = "exportadores top" if query.is_mirror else "socios top"
    top = ", ".join(str(p) for p, _ in who.most_common(5))
    span = f"{months[0]}–{months[-1]}" if months else "sin datos"
    return f"{len(records):>5} registros · meses {span} ({len(months)}) · {label} (código): {top}"


# ---------------------------------------------------------------- disponibilidad
def availability_report(session: requests.Session, api_key: str, conn, batch_id: int,
                        reporters: dict[int, str], since_year: int) -> dict[int, list[str]]:
    """
    Pregunta a Comtrade qué meses ha publicado cada reporter (getDa) y muestra los huecos.
    Devuelve {reporter: [periodos AAAAMM disponibles desde since_year]}.
    """
    out: dict[int, list[str]] = {}
    print(f"\nDisponibilidad mensual publicada en Comtrade (desde {since_year}):")
    for code, iso3 in reporters.items():
        params = {"reporterCode": code}
        payload = _get(session, DA_URL, params, api_key, f"getDa {iso3}")
        save_raw_response(conn, batch_id, "comtrade_da", DA_URL, params, payload)
        periods = sorted({str(r.get("period")) for r in payload.get("data") or []
                          if str(r.get("period", "")).isdigit() and int(str(r["period"])[:4]) >= since_year})
        out[code] = periods
        by_year: dict[str, int] = defaultdict(int)
        for p in periods:
            by_year[p[:4]] += 1
        detail = " · ".join(f"{y}: {n}/12" for y, n in sorted(by_year.items())) or "ningún mes"
        last = periods[-1] if periods else "—"
        print(f"  {iso3} ({code}): último mes publicado {last} · {detail}")
    return out


# ---------------------------------------------------------------- ejecución
def run(start_year: int, end_year: int, refresh: bool = False, dry_run: bool = False,
        session: requests.Session | None = None, pause: float = PAUSE_SECONDS,
        check_availability: bool = True) -> dict:
    to_fetch, from_cache = build_plan(start_year, end_year, refresh)
    n_da = 2 if check_availability else 0
    print(f"Plan Comtrade {start_year}–{end_year}: {len(to_fetch)} consultas de datos + {n_da} de "
          f"disponibilidad · {len(from_cache)} servidas desde caché")
    print(f"  Cupo diario gratuito: 500 consultas → este plan usa {len(to_fetch) + n_da}")
    if dry_run:
        for q in to_fetch:
            print(f"  · API   {q.label:<6} {q.flow} {q.year}")
        for q in from_cache:
            print(f"  · caché {q.label:<6} {q.flow} {q.year}")
        return {"fetched": 0, "cached": len(from_cache), "new_raw": 0, "records": 0}

    api_key = settings.comtrade_api_key
    if not api_key:
        raise SystemExit("Falta COMTRADE_API_KEY en .env (ver comtradedeveloper.un.org/profile)")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    session = session or requests.Session()
    stats = {"fetched": 0, "cached": len(from_cache), "new_raw": 0, "records": 0,
             "mirror_records": 0, "availability": {}}
    engine = get_engine("etl")

    with track_batch(SOURCE, {"start_year": start_year, "end_year": end_year, "refresh": refresh,
                              "hs": HS_CODES, "mirror_reporters": list(MIRROR_REPORTERS)}) as batch:
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
            if q.is_mirror:
                stats["mirror_records"] += len(records)
            batch.rows_loaded += len(records) if is_new else 0
            tag = "nuevo " if is_new else "igual "
            print(f"  [{i:>2}/{len(jobs)}] {q.label:<6} {q.flow} {q.year} · "
                  f"{'API  ' if origin else 'caché'} · {tag}· {summarize(q, records)}")

        if check_availability:
            with engine.begin() as conn:
                stats["availability"] = availability_report(
                    session, api_key, conn, batch.batch_id, {156: "CHN", 218: "ECU"}, max(start_year, end_year - 2))

    print(f"\nResumen: {stats['fetched']} llamadas de datos · {stats['new_raw']} respuestas nuevas en bronze · "
          f"{stats['records']} registros ({stats['mirror_records']} espejo)")
    return stats


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Extrae comercio de cerdo de UN Comtrade a bronze")
    p.add_argument("--start-year", type=int, default=settings.start_year)
    p.add_argument("--end-year", type=int, default=date.today().year)
    p.add_argument("--refresh", action="store_true", help="ignora la caché y pide todo de nuevo")
    p.add_argument("--dry-run", action="store_true", help="solo muestra el plan")
    p.add_argument("--no-availability", action="store_true", help="omite la consulta de disponibilidad")
    a = p.parse_args(argv)
    print("=== Pork to China · Fase 4 · extracción UN Comtrade ===\n")
    run(a.start_year, a.end_year, refresh=a.refresh, dry_run=a.dry_run,
        check_availability=not a.no_availability)
    return 0


if __name__ == "__main__":
    sys.exit(main())
