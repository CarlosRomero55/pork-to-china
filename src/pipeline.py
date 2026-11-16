"""
pipeline.py · Fase 8 · Orquestación de punta a punta

Corre las etapas en orden y se detiene en la primera que falla:
    migraciones → [extracción] → silver Comtrade → silver USDA → validación → gold → consultas → pruebas

- Cada etapa corre como subproceso aislado (`python -m src.<módulo>`): un error en una etapa
  no deja estado a medias en las demás, y su código de salida decide si se continúa.
- Cada corrida y cada etapa quedan registradas en pork_bronze.etl_run / etl_run_stage
  (inicio, fin, duración, estado, código de salida y las últimas líneas de la salida).
  La salida completa de cada etapa queda en logs/runs/.
- Un candado de MySQL (GET_LOCK) impide dos corridas a la vez.
- Es idempotente: correrlo dos veces seguidas deja la base igual (todas las cargas son upsert
  o reconstrucción completa).

Uso:
    python -m src.pipeline                 # sin extracción (usa lo que ya está en bronze)
    python -m src.pipeline --extract       # incluye la descarga de Comtrade y USDA (usa tu llave)
    python -m src.pipeline --from validate # retoma desde una etapa
"""
from __future__ import annotations

import argparse
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import text

from src.config import LOGS_DIR, ROOT_DIR
from src.db import BRONZE, get_engine
from src.logging_setup import get_logger
from src.migrate import migrate

log = get_logger(__name__)

LOCK_NAME = "pork_to_china_pipeline"
TAIL_LINES = 12


@dataclass(frozen=True)
class Stage:
    name: str
    args: tuple[str, ...]             # argumentos para el intérprete de Python
    label: str
    extract: bool = False             # True = solo corre con --extract


STAGES: tuple[Stage, ...] = (
    Stage("extract_comtrade", ("-m", "src.extract_comtrade"), "Extracción UN Comtrade → bronze", extract=True),
    Stage("extract_psd", ("-m", "src.extract_psd"), "Extracción USDA PSD → bronze", extract=True),
    Stage("silver_comtrade", ("-m", "src.harmonize"), "Comtrade: bronze → silver"),
    Stage("silver_psd", ("-m", "src.harmonize_psd"), "USDA PSD: bronze → silver"),
    Stage("validate", ("-m", "src.validate"), "Validación de calidad (12 reglas)"),
    Stage("gold", ("-m", "src.build_gold"), "Silver → gold (esquema estrella)"),
    Stage("queries", ("-m", "src.run_queries"), "Consultas de negocio → docs/queries.md"),
    Stage("tests", ("-m", "pytest", "tests", "-q", "-p", "no:warnings"), "Suite de pruebas"),
)


@dataclass
class StageResult:
    stage: str
    status: str                       # ok · failed · skipped
    started: datetime | None = None
    finished: datetime | None = None
    exit_code: int | None = None
    tail: str = ""

    @property
    def duration(self) -> float | None:
        return (self.finished - self.started).total_seconds() if self.started and self.finished else None


@dataclass
class RunResult:
    run_id: int
    status: str
    stages: list[StageResult] = field(default_factory=list)


def select_stages(extract: bool, start_from: str | None, stages=STAGES) -> list[Stage]:
    chosen = [s for s in stages if extract or not s.extract]
    if start_from:
        names = [s.name for s in chosen]
        if start_from not in names:
            raise SystemExit(f"Etapa desconocida: {start_from}. Opciones: {', '.join(names)}")
        chosen = chosen[names.index(start_from):]
    return chosen


def run_stage(stage: Stage, run_id: int, order: int) -> StageResult:
    """Corre una etapa como subproceso; guarda la salida completa en logs/runs/."""
    res = StageResult(stage.name, "failed", started=datetime.now())
    proc = subprocess.run([sys.executable, *stage.args], cwd=ROOT_DIR, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    res.finished, res.exit_code = datetime.now(), proc.returncode
    output = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
    log_dir = LOGS_DIR / "runs"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / f"run_{run_id:05d}_{order:02d}_{stage.name}.log").write_text(output, encoding="utf-8")
    useful = [ln for ln in output.splitlines() if ln.strip() and not ln.startswith("INFO")]
    res.tail = "\n".join(useful[-TAIL_LINES:])
    res.status = "ok" if proc.returncode == 0 else "failed"
    return res


def _save_stage(conn, run_id: int, order: int, r: StageResult) -> None:
    conn.execute(text(f"""
        INSERT INTO {BRONZE}.etl_run_stage
          (run_id, stage_order, stage, status, started_at, finished_at, duration_s, exit_code, output_tail)
        VALUES (:r, :o, :s, :st, :a, :b, :d, :e, :t)"""),
        {"r": run_id, "o": order, "s": r.stage, "st": r.status, "a": r.started, "b": r.finished,
         "d": round(r.duration, 2) if r.duration is not None else None, "e": r.exit_code, "t": r.tail or None})


def run_pipeline(stages: list[Stage], trigger: str = "manual", lock_name: str = LOCK_NAME,
                 do_migrate: bool = True, echo=print) -> RunResult:
    engine = get_engine("etl")
    if do_migrate:                     # las migraciones crean, entre otras, la tabla etl_run
        t0 = datetime.now()
        applied = migrate(engine)
        mig = StageResult("migrate", "ok", t0, datetime.now(), 0,
                          "aplicadas: " + (", ".join(applied) if applied else "ninguna pendiente"))
    with engine.connect() as lock_conn:              # el candado vive mientras dure esta conexión
        if lock_conn.execute(text("SELECT GET_LOCK(:n, 0)"), {"n": lock_name}).scalar() != 1:
            raise RuntimeError("Ya hay otra corrida del pipeline en curso (candado ocupado).")
        try:
            with engine.begin() as c:
                # Una corrida que quedó 'running' sin candado murió a medias: se marca como abortada
                c.execute(text(f"UPDATE {BRONZE}.etl_run SET status='aborted' "
                               f"WHERE status='running' AND trigger_src=:t"), {"t": trigger})
                run_id = c.execute(text(f"""INSERT INTO {BRONZE}.etl_run (trigger_src, stages, host)
                                            VALUES (:t, :s, :h)"""),
                                   {"t": trigger, "s": ",".join(["migrate"] * do_migrate + [s.name for s in stages]),
                                    "h": socket.gethostname()[:80]}).lastrowid
            result = RunResult(run_id, "ok")
            order = 0
            if do_migrate:
                order += 1
                result.stages.append(mig)
                with engine.begin() as c:
                    _save_stage(c, run_id, order, mig)
                echo(f"[{order}] {'Migraciones':<38} OK  {mig.duration:6.1f} s  · {mig.tail}")
            failed = False
            for st in stages:
                order += 1
                if failed:
                    r = StageResult(st.name, "skipped")
                else:
                    r = run_stage(st, run_id, order)
                    mark = "OK " if r.status == "ok" else "ERROR"
                    echo(f"[{order}] {st.label:<38} {mark} {r.duration:6.1f} s")
                    if r.status == "failed":
                        failed = True
                        echo("      " + r.tail.replace("\n", "\n      "))
                result.stages.append(r)
                with engine.begin() as c:
                    _save_stage(c, run_id, order, r)
            result.status = "failed" if failed else "ok"
            with engine.begin() as c:
                c.execute(text(f"UPDATE {BRONZE}.etl_run SET status=:s, finished_at=NOW(3) WHERE run_id=:r"),
                          {"s": result.status, "r": run_id})
            return result
        finally:
            lock_conn.execute(text("SELECT RELEASE_LOCK(:n)"), {"n": lock_name})


def history(n: int = 5) -> None:
    with get_engine("etl").connect() as c:
        rows = c.execute(text(f"""
            SELECT r.run_id, r.started_at, r.status,
                   TIMESTAMPDIFF(SECOND, r.started_at, r.finished_at) AS seg,
                   SUM(s.status='ok') AS ok, SUM(s.status='failed') AS err, SUM(s.status='skipped') AS skip
            FROM {BRONZE}.etl_run r LEFT JOIN {BRONZE}.etl_run_stage s ON s.run_id = r.run_id
            WHERE r.trigger_src <> 'pytest'
            GROUP BY r.run_id ORDER BY r.run_id DESC LIMIT :n"""), {"n": n}).all()
    print("\nÚltimas corridas (pork_bronze.etl_run)")
    print("  corrida  inicio               estado    seg  etapas ok/error/omitidas")
    for r in rows:
        print(f"  {r.run_id:>7}  {r.started_at:%Y-%m-%d %H:%M:%S}  {r.status:<8} {r.seg if r.seg is not None else '—':>5}"
              f"  {int(r.ok or 0)}/{int(r.err or 0)}/{int(r.skip or 0)}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Pipeline completo de Pork to China")
    p.add_argument("--extract", action="store_true", help="incluye la extracción (usa tu llave de Comtrade)")
    p.add_argument("--from", dest="start_from", help="retoma desde esta etapa")
    a = p.parse_args(argv)
    stages = select_stages(a.extract, a.start_from)
    print("=== Pork to China · Fase 8 · pipeline completo ===")
    print("Etapas: migrate → " + " → ".join(s.name for s in stages) + "\n")
    t0 = time.perf_counter()
    try:
        res = run_pipeline(stages)
    except RuntimeError as e:
        print(f"\n{e}")
        return 2
    total = time.perf_counter() - t0
    history()
    if res.status == "ok":
        print(f"\nCorrida {res.run_id}: OK en {total:.0f} s.")
        return 0
    bad = next(s for s in res.stages if s.status == "failed")
    print(f"\nCorrida {res.run_id}: FALLÓ en la etapa '{bad.stage}'. Salida completa en "
          f"logs\\runs\\run_{res.run_id:05d}_*_{bad.stage}.log")
    return 1


if __name__ == "__main__":
    sys.exit(main())
