"""
Pork to China · Fase 15.2 · Policy brief para Agrocalidad y el Ministerio de Producción

Genera, con las cifras de gold en cada corrida del pipeline:
  docs/policy_brief.md      el texto del brief (para leer en GitHub)
  docs/policy_brief.pdf     la versión de 2 páginas A4 (matplotlib, sin librerías nuevas)
  docs/img/brief_*.png      los dos gráficos

El texto y el PDF salen de la MISMA lista de bloques (build_blocks), así nunca dicen cosas distintas.
Ninguna cifra está escrita a mano: todas vienen de figures(), que lee gold y silver.
Las propuestas son recomendaciones del analista; no se atribuyen posiciones ni compromisos a las instituciones.

Uso:  python -m src.policy_brief
"""
from __future__ import annotations

import sys
import textwrap
from datetime import date

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from sqlalchemy import text  # noqa: E402

from src.config import ROOT_DIR  # noqa: E402
from src.db import GOLD, SILVER, get_engine  # noqa: E402

DOCS = ROOT_DIR / "docs"
MD = DOCS / "policy_brief.md"
PDF = DOCS / "policy_brief.pdf"
IMG_SHARE = DOCS / "img" / "brief_us_share.png"
IMG_MARGIN = DOCS / "img" / "brief_margin.png"

# Paleta del tablero (validada para daltonismo); texto siempre en tinta, nunca del color de la serie
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#6b6a65", "#e6e5e1", "#ffffff"
BLUE, ORANGE, RED, GRAY = "#2a78d6", "#eb6834", "#c4312f", "#b9b8b2"
BIG_SHARE, HIGH_BREED = 5.0, 75.0          # mismo criterio de "provincia candidata" que la página 5


def n(v: float, d: int = 0) -> str:
    """Número en formato español: punto de miles, coma decimal."""
    s = f"{v:,.{d}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


# ---------------------------------------------------------------- cifras
def figures(conn) -> dict:
    f: dict = {}
    q = (ROOT_DIR / "sql" / "queries" / "q01_trade_diversion.sql").read_text(encoding="utf-8")
    div = pd.read_sql(text(q), conn)
    us = div[(div["grupo"] == "Vísceras") & (div["proveedor"] == "Estados Unidos")].iloc[0]
    f["us_offal_pp"] = float(us.cambio_pp)
    f["us_offal_before"], f["us_offal_after"] = float(us.part_antes), float(us.part_despues)

    coef = pd.read_sql(text(f"SELECT term, estimate, p FROM {GOLD}.fact_its_coef WHERE model = 'share_value' "
                            "AND term IN ('level_2018', 'level_2020')"), conn).set_index("term")
    last = pd.read_sql(text(f"SELECT observed FROM {GOLD}.fact_its_series WHERE model = 'share_value' AND is_gap = 0 "
                            "ORDER BY date DESC LIMIT 3"), conn)["observed"]
    f["us_share_last3"] = float(last.mean())
    f["its_2018"], f["its_2020"] = float(coef.loc["level_2018", "estimate"]), float(coef.loc["level_2020", "estimate"])

    off = conn.execute(text(f"""SELECT SUM(f.tonnes), SUM(f.value_usd) FROM {GOLD}.fact_china_imports f
        JOIN {GOLD}.dim_product p ON p.product_key = f.product_key AND p.hs_code = '020649'
        WHERE f.basis = 'mirror' AND f.date_key BETWEEN 20250101 AND 20251201""")).one()
    f["offal_t_2025"], f["offal_usd_2025"] = float(off[0]), float(off[1])

    tr = pd.read_sql(text(f"SELECT * FROM {GOLD}.fact_trigger"), conn).set_index("trigger_code")
    f["offal_now"], f["offal_be"] = float(tr.loc["D1", "current_value"]), float(tr.loc["D1", "threshold"])
    f["fob_now"], f["fob_be"] = float(tr.loc["D2", "current_value"]), float(tr.loc["D2", "threshold"])
    f["fob_label"] = tr.loc["D2", "current_es"]

    a = pd.read_sql(text(f"""SELECT a.name, a.value_base FROM {SILVER}.assumption a
        WHERE a.version = (SELECT MAX(b.version) FROM {SILVER}.assumption b WHERE b.name = a.name)"""), conn)
    a = a.set_index("name")["value_base"].astype(float)
    f["var_cost"] = float(a["processing_cost_usd_kg"] + a["freezing_cost_usd_kg"] + a["export_logistics_usd_kg"])
    f["margin_now"] = f["fob_now"] - f["offal_now"] - f["var_cost"]
    f["capacity_t"] = float(a["agroporc_capacity_t"])

    res = pd.read_sql(text(f"SELECT npv_usd FROM {GOLD}.fact_scenario_result"), conn)
    f["n_scen"], f["n_neg"] = len(res), int((res["npv_usd"] < 0).sum())
    cap = pd.read_sql(text(f"""SELECT m.som_cap_t FROM {GOLD}.fact_scenario_market m
        JOIN {GOLD}.dim_scenario s USING (scenario_key) WHERE s.code = 'B-up-6'"""), conn)["som_cap_t"]
    f["som_min"], f["som_max"] = float(cap.min()), float(cap.max())

    pp = pd.read_sql(text(f"SELECT province_name, share_year_pct, breed_pct FROM {GOLD}.v_dash_province_pigs"), conn)
    cand = pp[(pp.share_year_pct >= BIG_SHARE) & (pp.breed_pct >= HIGH_BREED)].sort_values("share_year_pct", ascending=False)
    f["cand_names"] = [c.replace(" de los Tsáchilas", "") for c in cand.province_name]
    f["cand_share"] = float(cand.share_year_pct.sum())

    bm = pd.read_sql(text(f"SELECT iso3, years_to_first_export FROM {GOLD}.v_dash_access_benchmark"), conn).set_index("iso3")
    f["years_cri"], f["years_bra"] = int(bm.loc["CRI"].iloc[0]), int(bm.loc["BRA"].iloc[0])
    return f


# ---------------------------------------------------------------- gráficos
def _style(ax) -> None:
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=8, length=0)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def chart_share(conn, out) -> None:
    s = pd.read_sql(text(f"SELECT date, observed, is_gap FROM {GOLD}.fact_its_series WHERE model = 'share_value' "
                         "ORDER BY date"), conn)
    s["date"] = pd.to_datetime(s["date"])
    s.loc[s["is_gap"] == 1, "observed"] = None
    fig, ax = plt.subplots(figsize=(7.2, 2.35), dpi=200)
    ax.plot(s["date"], s["observed"], color=BLUE, linewidth=1.6)
    for d, lab in (("2018-04-01", "aranceles 2018"), ("2020-02-01", "exclusiones 2020"), ("2025-03-01", "aranceles 2025")):
        ax.axvline(pd.Timestamp(d), color=INK, linewidth=0.8, linestyle=(0, (3, 3)))
        ax.text(pd.Timestamp(d), 1.0, " " + lab, transform=ax.get_xaxis_transform(), fontsize=7.5, color=INK, va="top")
    ax.set_ylabel("% del valor importado", fontsize=8, color=MUTED)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.set_title("Participación de EE. UU. en las vísceras de cerdo que importa China (mensual)", fontsize=9,
                 color=INK, loc="left", fontweight="bold")
    _style(ax)
    fig.tight_layout()
    fig.savefig(out, facecolor=SURFACE)
    plt.close(fig)


def chart_margin(f: dict, out) -> None:
    steps = [("China paga\n(FOB)", f["fob_now"], BLUE), ("Valor de la víscera\nen Ecuador", -f["offal_now"], RED),
             ("Proceso, frío y\nlogística a puerto", -f["var_cost"], RED)]
    fig, ax = plt.subplots(figsize=(7.2, 2.35), dpi=200)
    level = 0.0
    for i, (lab, v, c) in enumerate(steps):
        ax.bar(i, v, bottom=level, color=c, width=0.6, edgecolor=SURFACE, linewidth=2)
        ax.text(i, level + v + (0.04 if v > 0 else -0.04), n(v, 2), ha="center", va="bottom" if v > 0 else "top",
                fontsize=8, color=INK)
        level += v
    m = f["margin_now"]
    ax.bar(3, m, color=ORANGE, width=0.6, edgecolor=SURFACE, linewidth=2)
    ax.text(3, m - 0.04, n(m, 2), ha="center", va="top", fontsize=9, color=INK, fontweight="bold")
    ax.axhline(0, color=INK, linewidth=0.8)
    ax.set_xticks(range(4), [s[0] for s in steps] + ["Margen\npor kilo"], fontsize=8, color=INK)
    ax.set_ylabel("USD por kg", fontsize=8, color=MUTED)
    ax.yaxis.set_major_formatter(lambda v, _: n(v, 1))
    ax.set_ylim(min(m, 0) - 0.35, f["fob_now"] + 0.3)
    ax.set_title("Por qué vender más no ayuda: cada kilo exportado deja hoy un margen negativo", fontsize=9,
                 color=INK, loc="left", fontweight="bold")
    _style(ax)
    fig.tight_layout()
    fig.savefig(out, facecolor=SURFACE)
    plt.close(fig)


# ---------------------------------------------------------------- contenido
def build_blocks(f: dict, today: date) -> list[tuple]:
    cands = ", ".join(f["cand_names"][:-1]) + " y " + f["cand_names"][-1]
    pct_agro = 100 * f["som_max"] / f["offal_t_2025"]
    return [
        ("title", "Del arancel a la oportunidad: qué necesita Ecuador para vender vísceras de cerdo a China"),
        ("meta", f"Policy brief · Para: Agrocalidad y Ministerio de Producción, Comercio Exterior, Inversiones y Pesca · "
                 f"{today:%d-%m-%Y} · Carlos Romero, proyecto de portafolio Pork to China"),
        ("h2", "El problema"),
        ("p", "La guerra comercial entre Estados Unidos y China abrió un espacio para otros proveedores de cerdo. Ecuador "
              "no puede ocuparlo: no tiene permiso sanitario para exportar cerdo a China y, aun si lo tuviera, a los precios "
              "de hoy cada kilo exportado dejaría pérdida. Este documento propone tres acciones públicas que no dependen de "
              "ninguna empresa y que convierten la próxima ventana en una oportunidad real."),
        ("h2", "Lo que muestran los datos"),
        ("bullet", f"La ventana existe, pero se abre y se cierra. Tras los aranceles de 2025, Estados Unidos pasó de "
                   f"{n(f['us_offal_before'], 1)}% a {n(f['us_offal_after'], 1)}% de las vísceras que compra China "
                   f"({n(f['us_offal_pp'], 1)} puntos, en toneladas), pero en valor ya volvió a cerca del "
                   f"{n(f['us_share_last3'], 0)}% en los últimos meses. En 2018 perdió {n(abs(f['its_2018']), 1)} puntos y en 2020 recuperó "
                   f"{n(f['its_2020'], 1)} cuando llegaron las exclusiones (serie de tiempo interrumpida, 2015–2026)."),
        ("bullet", f"El acceso sanitario tarda. Costa Rica y Brasil necesitaron unos {f['years_cri']} años desde el inicio "
                   "del protocolo hasta el primer envío, y entraron siendo libres de peste porcina clásica (Brasil, por zonas). "
                   "En Ecuador la OMSA solo reconoce como libre la zona insular de Galápagos."),
        ("bullet", f"El mercado no es el límite; el margen sí. China importó {n(f['offal_t_2025'] / 1e6, 2)} millones de "
                   f"toneladas de vísceras congeladas (HS 020649) en 2025, por {n(f['offal_usd_2025'] / 1e9, 2)} mil millones "
                   f"de USD. Pero hoy China paga {n(f['fob_now'], 2)} USD/kg y la víscera vale {n(f['offal_now'], 2)} en Ecuador: "
                   f"con {n(f['var_cost'], 2)} de proceso y logística, el margen es {n(f['margin_now'], 2)} USD por kilo. Con margen "
                   f"negativo, más volumen significa más pérdida: el valor actual neto es negativo en {f['n_neg']} de "
                   f"{f['n_scen']} escenarios."),
        ("img", IMG_SHARE),
        ("img", IMG_MARGIN),
        ("pagebreak",),
        ("h2", "Tres propuestas (recomendaciones del analista)"),
        ("h3", "1. Una zona continental libre de peste porcina clásica, empezando por las provincias que más producen"),
        ("p", f"{cands} concentran el {n(f['cand_share'], 0)}% de los cerdos que se venden al año (ESPAC 2024) y tienen "
              f"al menos {n(HIGH_BREED, 0)}% de cerdos de raza. Una zona libre reconocida por la OMSA en esas provincias, como hizo "
              "Brasil con Santa Catarina, es la condición previa para cualquier protocolo con China."),
        ("who", "Quién lidera: Agrocalidad, con los productores (ASPE). Plazo sugerido: plan con metas por provincia en 2027 "
                "y expediente ante la OMSA cuando se cumplan los requisitos."),
        ("h3", "2. Abrir ya la conversación del protocolo sanitario con China, con las vísceras incluidas desde el inicio"),
        ("p", f"Si el proceso toma unos {f['years_cri']} años, esperar a tener la zona libre para empezar suma los dos plazos. "
              "Conviene avanzar en paralelo y pedir desde el principio carne y subproductos: Costa Rica exportó vísceras desde "
              "su primer envío mientras que Chile amplió su protocolo a subproductos congelados recién en 2024, trece años después de abrir el mercado."),
        ("who", "Quién lidera: Ministerio de Producción (negociación comercial) con Agrocalidad (autoridad sanitaria ante la "
                "GACC). Plazo sugerido: carta de interés y cuestionario sanitario en 2027."),
        ("h3", "3. Publicar el precio en planta de las vísceras y subproductos de cerdo"),
        ("p", "La variable que decide si exportar conviene no tiene serie pública. Este análisis tuvo que estimarla con los "
              "precios de productor del cuero y las patitas del SIPA y un factor de descuento tomado del pollo. Una serie "
              "mensual por provincia permitiría a cualquier empresa hacer este cálculo con datos reales."),
        ("who", "Quién lidera: SIPA (Ministerio de Agricultura y Ganadería), con apoyo del Ministerio de Producción. "
                "Plazo sugerido: primera publicación en 2027."),
        ("h2", "Qué cambiaría si se cumplen"),
        ("p", f"El acceso es necesario pero no suficiente. Con protocolo y zona libre, una empresa como la del caso "
              f"({n(f['capacity_t'], 0)} t/año de capacidad) podría colocar entre {n(f['som_min'], 0)} y {n(f['som_max'], 0)} "
              f"t/año en el escenario central, apenas el {n(pct_agro, 2)}% de lo que importa China: Ecuador sería tomador de "
              f"precio. Por eso la inversión solo conviene si además la víscera se consigue a {n(f['offal_be'], 2)} USD/kg o "
              f"menos en planta, o si el precio en China sube a {n(f['fob_be'], 2)} o más. Las propuestas 1 y 2 abren la "
              "puerta; la 3 permite saber, con datos públicos, cuándo cruzarla."),
        ("h2", "Fuentes y límites"),
        ("small", "UN Comtrade (datos espejo de las importaciones de China, 2015–2026); USDA FAS PSD; INEC, ESPAC 2024; OMSA, "
                  "Resolución 26 (2024) sobre peste porcina clásica; Agrocalidad (campaña de vacunación 2026); SIPA/MAG; "
                  "benchmark de acceso de Chile, Costa Rica y Brasil (prensa sectorial). Modelo financiero y Monte Carlo del "
                  "proyecto: github.com/CarlosRomero55/pork-to-china. AgroPorc Ecuador es una empresa ficticia; las "
                  "propuestas son recomendaciones del autor y no representan la posición de ninguna institución. No es "
                  "asesoría de inversión."),
    ]


def to_markdown(blocks: list[tuple]) -> str:
    out = []
    for b in blocks:
        kind = b[0]
        if kind == "title":
            out.append(f"# {b[1]}\n")
        elif kind == "meta":
            out.append(f"*{b[1]}*\n")
        elif kind == "h2":
            out.append(f"## {b[1]}\n")
        elif kind == "h3":
            out.append(f"### {b[1]}\n")
        elif kind == "bullet":
            out.append(f"- {b[1]}")
        elif kind == "img":
            out.append(f"\n![{b[1].stem}](img/{b[1].name})\n")
        elif kind == "who":
            out.append(f"> {b[1]}\n")
        elif kind in ("p", "small"):
            out.append(f"{b[1]}\n")
    md = "\n".join(out)
    return md.replace("\n- ", "\n- ").replace("\n\n- ", "\n\n- ") + "\n"


# ---------------------------------------------------------------- PDF
A4 = (8.27, 11.69)
LEFT, RIGHT, TOP, BOTTOM = 0.75, 0.75, 0.7, 0.6
STYLE = {  # tamaño, peso, color, ancho de línea en caracteres, interlineado (pulgadas), espacio después
    "title": (15, "bold", INK, 54, 0.25, 0.08), "meta": (8, "normal", MUTED, 118, 0.15, 0.14),
    "h2": (11.5, "bold", INK, 80, 0.2, 0.06), "h3": (9.5, "bold", INK, 100, 0.17, 0.03),
    "p": (9, "normal", INK, 108, 0.165, 0.1), "bullet": (9, "normal", INK, 104, 0.165, 0.07),
    "who": (8.5, "normal", "#3a3935", 112, 0.155, 0.12), "small": (7.5, "normal", MUTED, 128, 0.135, 0.0),
}


def to_pdf(blocks: list[tuple], out) -> int:
    pages: list[list[tuple]] = [[]]
    for b in blocks:
        if b[0] == "pagebreak":
            pages.append([])
        else:
            pages[-1].append(b)
    width = A4[0] - LEFT - RIGHT
    with PdfPages(out, metadata={"Title": "Policy brief · Pork to China", "Author": "Carlos Romero"}) as pdf:
        for i, page in enumerate(pages, 1):
            fig = plt.figure(figsize=A4)
            y = A4[1] - TOP
            for b in page:
                kind = b[0]
                if kind == "img":
                    img = plt.imread(b[1])
                    h = width * img.shape[0] / img.shape[1]
                    ax = fig.add_axes([LEFT / A4[0], (y - h) / A4[1], width / A4[0], h / A4[1]])
                    ax.imshow(img)
                    ax.axis("off")
                    y -= h + 0.08
                    continue
                size, weight, color, wrap, lead, after = STYLE[kind]
                indent = 0.18 if kind == "bullet" else 0.0
                lines = textwrap.wrap(b[1], wrap)
                if kind == "bullet":
                    fig.text((LEFT + 0.04) / A4[0], y / A4[1], "•", fontsize=size, color=BLUE, va="top")
                if kind == "h2":
                    y -= 0.06
                for line in lines:
                    fig.text((LEFT + indent) / A4[0], y / A4[1], line, fontsize=size, fontweight=weight, color=color,
                             va="top", style="italic" if kind == "who" else "normal")
                    y -= lead
                y -= after
                if y < BOTTOM:
                    raise ValueError(f"La página {i} se desborda: recorta el texto")
            fig.text(LEFT / A4[0], 0.35 / A4[1], f"Pork to China · policy brief · página {i} de {len(pages)}",
                     fontsize=7, color=MUTED)
            pdf.savefig(fig)
            plt.close(fig)
    return len(pages)


def main() -> int:
    print("=== Pork to China · Fase 15.2 · Policy brief ===\n")
    with get_engine("etl").connect() as conn:
        f = figures(conn)
        chart_share(conn, IMG_SHARE)
    chart_margin(f, IMG_MARGIN)
    blocks = build_blocks(f, date.today())
    MD.write_text(to_markdown(blocks), encoding="utf-8")
    pages = to_pdf(blocks, PDF)
    print(f"docs/policy_brief.md · docs/policy_brief.pdf ({pages} páginas) · 2 gráficos en docs/img/")
    print(f"Margen por kilo hoy: {n(f['margin_now'], 2)} USD · VAN negativo en {f['n_neg']} de {f['n_scen']} escenarios")
    return 0


if __name__ == "__main__":
    sys.exit(main())
