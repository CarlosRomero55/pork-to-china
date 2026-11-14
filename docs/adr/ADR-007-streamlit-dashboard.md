# ADR-007 · Streamlit como capa de visualización (en lugar de Power BI)

- **Estado:** Aceptada
- **Fecha:** 2026-11-13

## Contexto
El proyecto debe poder mostrarse a reclutadores con **un enlace que abran y usen sin instalar nada**. Opciones evaluadas:
- **Power BI:** con una cuenta individual gratuita no se puede crear el enlace público ("Publish to web"); quedaría en capturas o video.
- **Tableau Public:** publica gratis, pero no se conecta a MySQL (hay que exportar a CSV o Excel) y el simulador queda limitado a parámetros.
- **Streamlit:** gratis, se publica en Streamlit Community Cloud, se conecta por código y permite que el simulador What-If recalcule VAN, TIR y equilibrio en vivo con las mismas funciones de Python que prueba pytest.

## Decisión
La visualización y el simulador se construyen en **Streamlit** (Fase 12), con Plotly para los gráficos. Lee solo la capa gold (usuario `pork_bi`, de solo lectura).

## Consecuencias
- (+) Un enlace público e interactivo para el portafolio y la página web.
- (+) El simulador usa el mismo código financiero probado (`src/scenarios.py`): una sola fuente de verdad, sin duplicar fórmulas en DAX.
- (+) Muestra más Python, que es transversal a Data Analytics y Data Engineering.
- (−) La app pública en la nube no puede leer el MySQL local. Para la versión publicada se exportará gold a archivos Parquet versionados (decisión a confirmar en la Fase 12), y en local seguirá leyendo MySQL.
- (−) Power BI es lo que más piden las vacantes en Ecuador. Queda como opción para un dashboard complementario más adelante: la capa gold ya le sirve sin cambios.
