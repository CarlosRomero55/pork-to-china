"""
test_harmonize_psd.py · USDA PSD: bronze → silver y regla R12 (oferta = demanda).
Las pruebas con base de datos corren en una transacción que se revierte.
"""
import io
import zipfile

import pytest
from sqlalchemy import text

from src import harmonize_psd as hp
from src.db import BRONZE, SILVER, get_engine
from src.extract_psd import read_pork_from_zip
from src.validate import r12_psd_balance

HEADER = ("Commodity_Code,Commodity_Description,Country_Code,Country_Name,Market_Year,Calendar_Year,Month,"
          "Attribute_ID,Attribute_Description,Unit_ID,Unit_Description,Value\n")


def row(code, name, year, attr, value):
    return f'0113000,"Meat, Swine",{code},{name},{year},2026,10,1,{attr},21,(1000 MT CWE),{value}\n'


def balanced(code, name, year, prod=100, imp=20, cons=110, exp=10):
    return "".join(row(code, name, year, a, v) for a, v in [
        ("Beginning Stocks", 0), ("Production", prod), ("Imports", imp), ("Total Supply", prod + imp),
        ("Domestic Consumption", cons), ("Exports", exp), ("Ending Stocks", 0),
        ("Total Distribution", cons + exp)])


def make_zip(csv):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("psd_livestock.csv", HEADER + csv)
    return buf.getvalue()


def test_na_country_code_is_not_missing():
    """'NA' (Antillas Neerlandesas) es un código, no un dato faltante."""
    df = read_pork_from_zip(make_zip(row("NA", "Netherlands Antilles", 2000, "Production", 1)))
    assert df["countrycode"].iloc[0] == "NA"


def test_psd_codes_that_look_like_iso_are_mapped_explicitly():
    assert hp.PSD_TO_ISO3["AS"] == "AUS" and hp.PSD_TO_ISO3["AU"] == "AUT"
    assert hp.PSD_TO_ISO3["CI"] == "CHL" and hp.PSD_TO_ISO3["CH"] == "CHN"


@pytest.fixture()
def conn_with_zip(tmp_path):
    """Registra en bronze un ZIP de prueba (año 2099) dentro de una transacción que se revierte."""
    zpath = tmp_path / "psd_test.zip"
    zpath.write_bytes(make_zip(balanced("CH", "China", 2099) + balanced("ZZ", "Atlantis", 2099)
                               + balanced("EC", "Ecuador", 2010)))
    with get_engine("etl").connect() as c:
        trans = c.begin()
        b = c.execute(text(f"INSERT INTO {BRONZE}.extract_batch (source_name) VALUES ('pytest')")).lastrowid
        c.execute(text(f"""INSERT INTO {BRONZE}.raw_file (batch_id, source_name, file_name, stored_path, file_hash)
                           VALUES (:b, 'usda_psd', 'psd_test.zip', :p, REPEAT('a', 64))"""),
                  {"b": b, "p": str(zpath)})
        yield c
        trans.rollback()


def test_build_maps_known_keeps_unknown(conn_with_zip):
    countries, balance, info = hp.build(conn_with_zip, 2090)
    ch = countries.set_index("psd_code")
    assert ch.loc["CH", "country_id"] > 0                 # China vinculada al catálogo
    assert "ZZ" in ch.index and ch.loc["ZZ"].isna()["country_id"]   # desconocido: se conserva, sin id
    assert set(balance["market_year"]) == {2099}          # filtra por año de inicio
    assert info["ecuador_last_year"] == 2010              # informa hasta cuándo USDA siguió a Ecuador


def test_load_is_idempotent(conn_with_zip):
    countries, balance, _ = hp.build(conn_with_zip, 2090)
    hp.upsert_df(conn_with_zip, countries, SILVER, "psd_country", ["name", "country_id", "country_group_id"])
    r1 = hp.upsert_df(conn_with_zip, balance, SILVER, "psd_balance", ["value", "unit", "released", "batch_id"])
    r2 = hp.upsert_df(conn_with_zip, balance, SILVER, "psd_balance", ["value", "unit", "released", "batch_id"])
    assert r1.inserted == 16 and r2.inserted == 0 and r2.updated == 0


def test_r12_detects_unbalanced_sheet(conn_with_zip):
    before = r12_psd_balance(conn_with_zip).affected
    conn_with_zip.execute(text(f"INSERT IGNORE INTO {SILVER}.psd_country (psd_code, name) VALUES ('ZY','Roto')"))
    src = conn_with_zip.execute(text(f"SELECT source_id FROM {SILVER}.source WHERE name='usda_psd'")).scalar()
    for attr, v in [("Production", 100), ("Imports", 50), ("Total Supply", 150),
                    ("Domestic Consumption", 100), ("Exports", 10), ("Total Distribution", 110)]:   # 150 ≠ 110
        conn_with_zip.execute(text(f"""INSERT INTO {SILVER}.psd_balance
            (psd_code, market_year, attribute, value, unit, source_id, batch_id)
            VALUES ('ZY', 2099, :a, :v, '(1000 MT CWE)', :s, 0)"""), {"a": attr, "v": v, "s": src})
    after = r12_psd_balance(conn_with_zip)
    assert after.affected == before + 1 and "ZY 2099" in after.detail
