"""
db_setup.py · Fase 2 · Crea las bases bronze/silver/gold, los usuarios y los datos de referencia.

Uso en el PC (lo llama db_setup.ps1):
    python -m src.db_setup

Qué hace:
  1. Pide (oculto) la contraseña de root de MySQL y las contraseñas nuevas
     para los usuarios pork_etl (pipeline) y pork_bi (Power BI / API, solo lectura).
  2. Ejecuta sql/01_bronze.sql, 02_silver.sql, 03_gold.sql y sql/seed/*.sql.
  3. Crea los usuarios con mínimo privilegio y escribe DB_USER/DB_PASSWORD en .env.
  4. Verifica: conteo de tablas, filas sembradas, SCD2 sin solapes y el arancel
     total al cerdo de EE. UU. en 4 fechas clave (37%, 172%, 57%, 47%).

Todo es idempotente: se puede volver a correr sin romper nada.
Sin preguntas: si .env trae DB_USER=root (o otro admin) y DB_PASSWORD, se usan esas credenciales;
las contraseñas de pork_etl y pork_bi se generan solas y quedan en .env (root sale del .env).
Modo pruebas: exportar SETUP_ROOT_PASSWORD, SETUP_ETL_PASSWORD, SETUP_BI_PASSWORD.
"""
from __future__ import annotations

import getpass
import os
import re
import secrets
import sys
from pathlib import Path

import pymysql
from dotenv import set_key

from src.config import ROOT_DIR, SQL_DIR, settings

SQL_FILES = [
    SQL_DIR / "01_bronze.sql",
    SQL_DIR / "02_silver.sql",
    SQL_DIR / "03_gold.sql",
    *sorted((SQL_DIR / "seed").glob("*.sql")),
]
SCHEMAS = (settings.db_bronze, settings.db_silver, settings.db_gold)


# ---------------------------------------------------------------- utilidades
def split_sql(text: str) -> list[str]:
    """Divide un archivo .sql en sentencias (quita comentarios de línea completa)."""
    lines = [ln for ln in text.splitlines() if not ln.strip().startswith("--")]
    parts = re.split(r";\s*$", "\n".join(lines), flags=re.MULTILINE)
    return [p.strip() for p in parts if p.strip()]


def ask_password(prompt: str, env_var: str, confirm: bool = False, allow_empty: bool = False) -> str:
    """Lee una contraseña del entorno (pruebas) o del teclado sin mostrarla."""
    if env_var in os.environ:
        return os.environ[env_var]
    while True:
        pwd = getpass.getpass(prompt)
        if not pwd and not allow_empty:
            print("  La contraseña no puede estar vacía.")
            continue
        if confirm and getpass.getpass("  Repítela: ") != pwd:
            print("  No coinciden, intenta de nuevo.")
            continue
        return pwd


def connect(user: str, password: str, database: str | None = None) -> pymysql.connections.Connection:
    return pymysql.connect(
        host=settings.db_host, port=settings.db_port, user=user, password=password,
        database=database, charset="utf8mb4", autocommit=True,
    )


# ---------------------------------------------------------------- pasos
def run_sql_files(conn) -> None:
    with conn.cursor() as cur:
        for path in SQL_FILES:
            stmts = split_sql(path.read_text(encoding="utf-8"))
            for stmt in stmts:
                cur.execute(stmt)
            print(f"  OK  {path.relative_to(ROOT_DIR)}  ({len(stmts)} sentencias)")


def create_users(conn, etl_pwd: str, bi_pwd: str) -> None:
    """Mínimo privilegio: pork_etl escribe en las 3 capas; pork_bi solo lee gold."""
    with conn.cursor() as cur:
        for user, pwd in (("pork_etl", etl_pwd), ("pork_bi", bi_pwd)):
            # %s se escapa del lado del cliente → la contraseña nunca se concatena a mano
            cur.execute("CREATE USER IF NOT EXISTS %s@'localhost' IDENTIFIED BY %s", (user, pwd))
            cur.execute("ALTER USER %s@'localhost' IDENTIFIED BY %s", (user, pwd))
        for schema in SCHEMAS:
            cur.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, DROP, "
                        f"CREATE VIEW, SHOW VIEW, REFERENCES ON `{schema}`.* TO 'pork_etl'@'localhost'")
        cur.execute(f"GRANT SELECT, SHOW VIEW ON `{settings.db_gold}`.* TO 'pork_bi'@'localhost'")
    print("  OK  usuarios pork_etl (lectura/escritura en 3 capas) y pork_bi (solo lectura en gold)")


def update_env(etl_pwd: str, bi_pwd: str) -> None:
    env_path = ROOT_DIR / ".env"
    if not env_path.exists():
        env_path.write_text((ROOT_DIR / ".env.example").read_text(encoding="utf-8"), encoding="utf-8")
    set_key(str(env_path), "DB_USER", "pork_etl", quote_mode="never")
    set_key(str(env_path), "DB_PASSWORD", etl_pwd, quote_mode="always")
    set_key(str(env_path), "BI_USER", "pork_bi", quote_mode="never")
    set_key(str(env_path), "BI_PASSWORD", bi_pwd, quote_mode="always")
    print("  OK  .env actualizado: DB_USER=pork_etl y BI_USER=pork_bi (contraseñas guardadas, no se muestran).")
    print("      La contraseña de root ya NO queda en .env.")


def verify(etl_pwd: str) -> bool:
    """Conecta como pork_etl (prueba los permisos) y revisa lo creado."""
    ok = True
    conn = connect("pork_etl", etl_pwd)
    with conn.cursor() as cur:
        print("\n  Tablas y vistas por capa:")
        for schema in SCHEMAS:
            cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=%s", (schema,))
            print(f"    {schema:<12} {cur.fetchone()[0]:>3}")

        print("\n  Filas de referencia sembradas:")
        for table in ("source", "country", "country_group_member", "hs_product",
                      "trade_measure", "assumption", "scenario", "province"):
            cur.execute(f"SELECT COUNT(*) FROM `{settings.db_silver}`.`{table}`")
            print(f"    silver.{table:<22} {cur.fetchone()[0]:>4}")
        cur.execute(f"SELECT COUNT(*), MIN(date), MAX(date) FROM `{settings.db_gold}`.dim_date")
        n, dmin, dmax = cur.fetchone()
        print(f"    gold.dim_date                 {n:>4}  ({dmin} a {dmax})")

        # SCD2: ninguna medida puede tener dos versiones que se solapen en el tiempo
        cur.execute(f"""
            SELECT COUNT(*) FROM `{settings.db_silver}`.trade_measure a
            JOIN `{settings.db_silver}`.trade_measure b
              ON a.imposing_id = b.imposing_id AND a.target_key = b.target_key
             AND a.hs_code = b.hs_code AND a.measure_type = b.measure_type
             AND a.measure_id < b.measure_id
             AND a.valid_from <= b.valid_to AND b.valid_from <= a.valid_to""")
        overlaps = cur.fetchone()[0]
        ok &= overlaps == 0
        print(f"\n  SCD2 · versiones solapadas: {overlaps}  {'OK' if overlaps == 0 else 'ERROR'}")

        # Prueba de negocio: arancel total al cerdo de EE. UU. (vísceras 020649) en 4 fechas
        print("\n  Arancel total de China al cerdo de EE. UU. (HS 020649), reconstruido con SCD2:")
        expected = {"2025-01-15": 37, "2025-04-20": 172, "2025-07-15": 57, "2026-11-13": 47}
        for day, exp in expected.items():
            cur.execute(f"""
                SELECT COALESCE(SUM(m.rate_pct), 0)
                FROM `{settings.db_silver}`.trade_measure m
                JOIN `{settings.db_silver}`.country cn ON cn.country_id = m.imposing_id AND cn.iso3 = 'CHN'
                LEFT JOIN `{settings.db_silver}`.country t ON t.country_id = m.target_id
                WHERE m.hs_code = '020649'
                  AND %s BETWEEN m.valid_from AND m.valid_to
                  AND (m.measure_type = 'mfn' OR t.iso3 = 'USA')""", (day,))
            total = float(cur.fetchone()[0])
            good = abs(total - exp) < 0.01
            ok &= good
            print(f"    {day}: {total:6.1f}%   (esperado {exp}%)  {'OK' if good else 'ERROR'}")
    conn.close()
    return ok


def connect_as_admin() -> tuple[pymysql.connections.Connection | None, str]:
    """Pide usuario y contraseña de administrador y los prueba ANTES de seguir (3 intentos)."""
    # Si el .env trae un usuario administrador (no pork_etl), se prueba primero sin preguntar nada
    env_user, env_pwd = os.getenv("DB_USER", ""), os.getenv("DB_PASSWORD", "")
    if env_user and env_user not in ("pork_etl", "pork_bi") and "SETUP_ROOT_PASSWORD" not in os.environ:
        try:
            conn = connect(env_user, env_pwd)
            print(f"  Conectado como {env_user} con las credenciales del .env.")
            return conn, env_user
        except pymysql.err.OperationalError as e:
            print(f"  Las credenciales del .env para '{env_user}' no funcionaron ({e.args[0]}); te las pido a mano.")

    default_user = os.getenv("SETUP_ROOT_USER", "root")
    for intento in range(1, 4):
        if "SETUP_ROOT_PASSWORD" in os.environ:
            user = default_user
        else:
            user = input(f"Usuario administrador de MySQL [{default_user}]: ").strip() or default_user
        pwd = ask_password(f"Contraseña de '{user}' (Enter si no tiene; no se guarda): ",
                           "SETUP_ROOT_PASSWORD", allow_empty=True)
        try:
            conn = connect(user, pwd)
            print(f"  Conectado como {user}.")
            return conn, user
        except pymysql.err.OperationalError as e:
            code = e.args[0]
            if code == 1045:
                print(f"  Acceso denegado para '{user}' (intento {intento}/3). Revisa la contraseña.")
            elif code == 2003:
                print(f"  No hay servidor MySQL en {settings.db_host}:{settings.db_port}. "
                      "¿Está encendido el servicio MySQL80? (services.msc)")
                return None, user
            else:
                print(f"  Error {code}: {e.args[1]}")
            if "SETUP_ROOT_PASSWORD" in os.environ:
                break
    return None, default_user


def main() -> int:
    print("=== Pork to China · Fase 2 · creación de la base de datos ===\n")
    root, _ = connect_as_admin()
    if root is None:
        print("\nNo se pudo entrar como administrador. Si no recuerdas la contraseña de root, avísale a Claude.")
        return 1

    # Contraseñas de los usuarios del proyecto: se reutilizan las del .env si ya existen;
    # si no, se generan aleatorias (24 caracteres) y se guardan en .env. No hay que escribir nada.
    etl_pwd = os.getenv("SETUP_ETL_PASSWORD") or (os.getenv("DB_PASSWORD") if os.getenv("DB_USER") == "pork_etl" else "") \
        or secrets.token_urlsafe(18)
    bi_pwd = os.getenv("SETUP_BI_PASSWORD") or os.getenv("BI_PASSWORD") or secrets.token_urlsafe(18)

    print("\n[1/3] Ejecutando scripts SQL")
    run_sql_files(root)
    print("[2/3] Usuarios y permisos")
    create_users(root, etl_pwd, bi_pwd)
    root.close()
    update_env(etl_pwd, bi_pwd)
    print("[3/3] Verificación (conectado como pork_etl)")
    ok = verify(etl_pwd)

    # Mínimo privilegio: pork_bi no debe ver silver
    bi = connect("pork_bi", bi_pwd)
    with bi.cursor() as cur:
        try:
            cur.execute(f"SELECT 1 FROM `{settings.db_silver}`.country LIMIT 1")
            print("\n  pork_bi puede leer silver: ERROR (debería estar bloqueado)")
            ok = False
        except pymysql.err.MySQLError:
            print("\n  pork_bi bloqueado en silver: OK (mínimo privilegio)")
    bi.close()

    print("\n" + ("Todo listo." if ok else "Hubo verificaciones con ERROR; pégale esta salida a Claude."))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
