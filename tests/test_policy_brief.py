"""
test_policy_brief.py · Fase 15.2 · el brief sale de gold, cabe en 2 páginas y sus cifras cuadran con el modelo.
"""
import pytest
from sqlalchemy import text

from src import policy_brief as pb
from src.db import get_engine


def test_spanish_number_format():
    assert pb.n(1234567.891, 2) == "1.234.567,89"
    assert pb.n(-0.16, 2) == "-0,16"
    assert pb.n(37.4) == "37"


@pytest.fixture(scope="module")
def figs():
    with get_engine("etl").connect() as c:
        if not c.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='pork_gold' "
                              "AND table_name='fact_trigger'")).scalar():
            pytest.skip("migración 022 no aplicada: corre .\\pipeline.ps1")
        yield pb.figures(c)


def test_margin_is_the_sum_of_its_parts(figs):
    assert figs["margin_now"] == pytest.approx(figs["fob_now"] - figs["offal_now"] - figs["var_cost"])


def test_figures_match_the_model(figs):
    with get_engine("etl").connect() as c:
        neg = c.execute(text("SELECT SUM(npv_usd < 0), COUNT(*) FROM pork_gold.fact_scenario_result")).one()
        d1 = c.execute(text("SELECT threshold FROM pork_gold.fact_trigger WHERE trigger_code = 'D1'")).scalar()
    assert (figs["n_neg"], figs["n_scen"]) == (int(neg[0]), int(neg[1]))
    assert figs["offal_be"] == pytest.approx(d1)
    assert 0 < figs["som_min"] <= figs["som_max"] < figs["offal_t_2025"]
    assert len(figs["cand_names"]) >= 1 and 0 < figs["cand_share"] < 100


def test_every_block_figure_is_in_the_markdown(figs):
    from datetime import date
    blocks = pb.build_blocks(figs, date(2026, 11, 17))
    md = pb.to_markdown(blocks)
    for v in (pb.n(figs["margin_now"], 2), pb.n(figs["offal_be"], 2), pb.n(figs["fob_be"], 2), pb.n(figs["fob_now"], 2)):
        assert v in md
    assert "recomendaciones del analista" in md and "ficticia" in md
    assert sum(1 for b in blocks if b[0] == "pagebreak") == 1


def test_pdf_has_two_pages(figs, tmp_path):
    pdfplumber = pytest.importorskip("pdfplumber")
    from datetime import date
    pb.chart_margin(figs, pb.IMG_MARGIN)
    if not pb.IMG_SHARE.exists():
        pytest.skip("falta el gráfico de participación: corre la etapa policy_brief")
    out = tmp_path / "brief.pdf"
    pages = pb.to_pdf(pb.build_blocks(figs, date(2026, 11, 17)), out)
    with pdfplumber.open(out) as pdf:
        assert pages == len(pdf.pages) == 2
        assert "Tres propuestas" in pdf.pages[1].extract_text()
