"""
test_espac.py · Fase 13.2 · lectura de los tabulados de la ESPAC (INEC), el mapa de provincias y la
carga en silver. El Excel de prueba se arma aquí mismo, con la misma forma que el del INEC.
"""
import json
from pathlib import Path

import openpyxl
import pytest
from sqlalchemy import text

from src import load_espac as le
from src.db import get_engine

GEO = Path(__file__).resolve().parents[1] / "src" / "dashboard" / "assets" / "ecuador_provinces.geojson"
NAMES = {"SIERRA": ["AZUAY", "BOLÍVAR", "CAÑAR", "CARCHI", "COTOPAXI", "CHIMBORAZO", "IMBABURA", "LOJA",
                    "PICHINCHA", "TUNGURAHUA", "SANTO DOMINGO DE LOS TSÁCHILAS"],
         "COSTA": ["EL ORO", "ESMERALDAS", "GUAYAS", "LOS RÍOS", "MANABÍ", "SANTA ELENA"],
         "AMAZÓNICA": ["MORONA SANTIAGO", "NAPO", "ORELLANA", "PASTAZA", "SUCUMBÍOS", "ZAMORA CHINCHIPE"]}


def fake_workbook(path: Path, drop: str | None = None) -> Path:
    """Excel con T57–T59 como los del INEC: título, totales, filas de región y provincias con tildes."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for sheet in ("T57", "T58", "T59"):
        ws = wb.create_sheet(sheet)
        ws.append(["Región y Provincia", "GANADO PORCINO"])
        ws.append(["TOTAL NACIONAL", 999, 1, 2, 3, 4, 5])
        for region, provs in NAMES.items():
            ws.append([f"REGIÓN {region}"])
            for i, p in enumerate(provs, start=1):
                if p == drop:
                    continue
                if sheet == "T57":       # existencia, <2m, >2m, ventas, <2m, >2m
                    ws.append([p, 1000 * i, 1, 2, 10 * i, 1, 2])
                elif sheet == "T58":     # total, de raza, mestizo, criollo
                    ws.append([p, 1000 * i, 500 * i, 1, 1])
                else:                    # cerdos al año
                    ws.append([p, 2000.4 * i])
        ws.append(["FUENTE: INSTITUTO NACIONAL DE ESTADÍSTICA Y CENSOS (INEC) ESPAC - 2024"])
    wb.save(path)
    return path


def test_norm_removes_accents_and_spaces():
    assert le.norm("  Región   Amazónica ") == "REGION AMAZONICA"
    assert le.norm("CAÑAR") == "CANAR"


def test_reads_all_provinces_with_region_and_values(tmp_path):
    df = le.read_espac(fake_workbook(tmp_path / "Tabulados_ESPAC_2024.xlsx")).set_index("dpa_code")
    assert len(df) == 23 and set(df.index) == set(le.DPA.values())
    assert df.loc["10", "province_name"] == "Imbabura" and df.loc["10", "region"] == "Sierra"
    assert df.loc["03", "province_name"] == "Cañar"
    assert df.loc["07", "region"] == "Costa" and df.loc["22", "region"] == "Amazonía"
    azuay = df.loc["01"]
    assert (azuay.stock_head, azuay.sales_q3_head, azuay.breed_head, azuay.pigs_per_year) == (1000, 10, 500, 2000)


def test_missing_province_is_an_error(tmp_path):
    with pytest.raises(ValueError, match="faltan"):
        le.read_espac(fake_workbook(tmp_path / "x.xlsx", drop="NAPO"))


def test_geojson_has_the_23_provinces_clockwise():
    geo = json.loads(GEO.read_text(encoding="utf-8"))
    assert {f["properties"]["dpa"] for f in geo["features"]} == set(le.DPA.values())
    for f in geo["features"]:
        polys = [f["geometry"]["coordinates"]] if f["geometry"]["type"] == "Polygon" else f["geometry"]["coordinates"]
        for poly in polys:
            ring = poly[0]
            area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(ring, ring[1:])) / 2
            assert area < 0, f["properties"]["name"]          # exterior en sentido horario (d3/Plotly)


@pytest.fixture(scope="module")
def loaded():
    with get_engine("bi").connect() as c:
        n = c.execute(text("SELECT COUNT(*) FROM pork_gold.v_dash_province_pigs")).scalar()
        if not n:
            pytest.skip("sin datos de la ESPAC: descarga los tabulados del INEC y corre .\\pipeline.ps1")
        yield c


def test_silver_has_23_provinces_and_shares_add_to_100(loaded):
    rows = loaded.execute(text("""
        SELECT survey_year, COUNT(*), SUM(share_year_pct) FROM pork_gold.v_dash_province_pigs
        GROUP BY survey_year""")).all()
    for _, n, total in rows:
        assert n == 23 and abs(float(total) - 100) < 0.1


def test_sanitary_status_has_source_and_csf_blocks(loaded):
    rows = dict(loaded.execute(text("SELECT disease, china_risk FROM pork_gold.v_dash_sanitary")).all())
    assert rows["Peste porcina clásica (PPC)"] == "bloquea"
    assert not loaded.execute(text("SELECT COUNT(*) FROM pork_gold.v_dash_sanitary WHERE source IS NULL")).scalar()
