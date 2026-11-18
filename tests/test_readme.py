"""
test_readme.py · Fase 16.1 · las cifras clave del README cuadran con gold (si el modelo cambia, la prueba avisa).
"""
from pathlib import Path

import pytest
from sqlalchemy import text

from src import policy_brief as pb
from src.db import get_engine

README = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")


def test_no_work_in_progress_banner():
    assert "Work in progress" not in README and "Resumen en español" in README


def test_linked_files_exist():
    root = Path(__file__).resolve().parents[1]
    for link in ("docs/recommendation.md", "docs/premortem.md", "docs/policy_brief.pdf", "docs/triggers.md",
                 "docs/img/dashboard_9_recomendacion.png", "docs/adr/ADR-011-serie-tiempo-interrumpida.md"):
        assert link in README and (root / link).exists(), link


@pytest.fixture(scope="module")
def figs():
    with get_engine("etl").connect() as c:
        if not c.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='pork_gold' "
                              "AND table_name='fact_trigger'")).scalar():
            pytest.skip("migración 022 no aplicada: corre .\\pipeline.ps1")
        f = pb.figures(c)
        mc = c.execute(text("SELECT MIN(p_npv_pos), MAX(p_npv_pos) FROM pork_gold.fact_mc_summary m "
                            "JOIN pork_gold.dim_scenario s USING (scenario_key) WHERE s.cert_year IS NOT NULL")).one()
        f["mc_min"], f["mc_max"] = float(mc[0]), float(mc[1])
        yield f


def test_key_figures_match_gold(figs):
    for v in (figs["fob_now"], figs["offal_now"], figs["var_cost"], figs["offal_be"], figs["fob_be"]):
        assert f"{v:.2f}" in README, v
    assert f"{figs['margin_now']:.2f}".replace("-", "−") in README
    assert f"**{figs['n_neg']} of {figs['n_scen']}**" in README
    assert f"{figs['us_offal_before']:.1f}% to {figs['us_offal_after']:.1f}%" in README
    assert f"lost {abs(figs['its_2018']):.1f} points and won back {figs['its_2020']:.1f}" in README
    assert f"**{figs['mc_min']:.0%}–{figs['mc_max']:.0%}**" in README
