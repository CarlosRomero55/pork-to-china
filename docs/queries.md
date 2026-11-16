# Consultas SQL de negocio

Generado por `src/run_queries.py` el 2026-11-16 con el usuario de solo lectura `pork_bi` sobre `pork_gold`. Cada consulta está en `sql/queries/`.

## q01_trade_diversion

**Pregunta:** ¿Quién ganó y quién perdió participación en China tras el arancel a EE. UU. (marzo 2025)? 12 meses antes (2024-03 a 2025-02) vs 12 meses después (2025-03 a 2026-02), carne y vísceras por separado.  
**Técnica:** CTE + agregación condicional + participación con SUM() OVER (PARTITION BY ...)  
**Fuente:** pork_gold.fact_china_imports, SOLO base espejo (lo que declaran los 12 exportadores): es la única base continua 2018–2026. Mezclar directo y espejo entre periodos sesga la comparación (ADR-008).  
**Lectura:** (datos a 2026-09) en carne perdieron los castigados con aranceles —Brasil −4,6 pp, Canadá −4,1 pp, EE. UU. −1,3 pp— y ganó España (+4,0 pp) pese al antidumping. En vísceras, el nicho de Ecuador, el gran perdedor es EE. UU. (−31%, −5,9 pp) y ganan España, Reino Unido y Dinamarca: el hueco lo llenó Europa.  

[Ver SQL](../sql/queries/q01_trade_diversion.sql) · 24 filas

| grupo | proveedor | t_antes | t_despues | cambio_pct | part_antes | part_despues | cambio_pp |
|---|---|---|---|---|---|---|---|
| Carne | España | 249.838 | 213.752 | -14,4 | 24,0 | 28,0 | 4,0 |
| Carne | Reino Unido | 42.326 | 46.153 | 9,0 | 4,1 | 6,0 | 2,0 |
| Carne | Chile | 66.173 | 62.159 | -6,1 | 6,4 | 8,1 | 1,8 |
| Carne | Dinamarca | 57.322 | 53.047 | -7,5 | 5,5 | 7,0 | 1,4 |
| Carne | Irlanda | 46.181 | 39.022 | -15,5 | 4,4 | 5,1 | 0,7 |
| Carne | Países Bajos | 61.809 | 47.481 | -23,2 | 5,9 | 6,2 | 0,3 |
| Carne | Polonia | 324 | 75 | -76,7 | 0,0 | 0,0 | 0,0 |
| Carne | Alemania | 1.271 | 418 | -67,1 | 0,1 | 0,1 | -0,1 |
| Carne | Francia | 46.030 | 33.272 | -27,7 | 4,4 | 4,4 | -0,1 |
| Carne | Estados Unidos | 151.977 | 101.178 | -33,4 | 14,6 | 13,3 | -1,3 |
| Carne | Canadá | 108.511 | 48.242 | -55,5 | 10,4 | 6,3 | -4,1 |
| Carne | Brasil | 209.236 | 118.464 | -43,4 | 20,1 | 15,5 | -4,6 |
| Vísceras | España | 282.173 | 267.925 | -5,0 | 23,7 | 26,0 | 2,3 |
| Vísceras | Reino Unido | 79.466 | 89.860 | 13,1 | 6,7 | 8,7 | 2,1 |
| Vísceras | Dinamarca | 128.328 | 128.818 | 0,4 | 10,8 | 12,5 | 1,7 |
| Vísceras | Canadá | 96.760 | 88.818 | -8,2 | 8,1 | 8,6 | 0,5 |
| Vísceras | Chile | 39.968 | 37.662 | -5,8 | 3,4 | 3,7 | 0,3 |
| Vísceras | Brasil | 20.980 | 20.634 | -1,6 | 1,8 | 2,0 | 0,2 |
| Vísceras | Alemania | 14 | 11 | -18,3 | 0,0 | 0,0 | 0,0 |
| Vísceras | Polonia | 82 | 0 | -100,0 | 0,0 | 0,0 | 0,0 |
| Vísceras | Irlanda | 16.475 | 13.500 | -18,1 | 1,4 | 1,3 | -0,1 |
| Vísceras | Países Bajos | 108.305 | 89.512 | -17,4 | 9,1 | 8,7 | -0,4 |
| Vísceras | Francia | 76.726 | 57.908 | -24,5 | 6,4 | 5,6 | -0,8 |
| Vísceras | Estados Unidos | 341.236 | 234.623 | -31,2 | 28,7 | 22,8 | -5,9 |

## q02_supplier_ranking

**Pregunta:** ¿Cómo cambió el ranking de proveedores de cerdo de China año a año (2018–2025)?  
**Técnica:** CTE + RANK() OVER (PARTITION BY año ORDER BY toneladas DESC) + pivoteo con MAX(CASE ...)  
**Fuente:** pork_gold.fact_china_imports, SOLO base espejo (lo que declaran los 12 exportadores): es la única base continua 2018–2026. Mezclar directo y espejo entre periodos sesga la comparación (ADR-008).  
**Lectura:** España es el n.º 1 desde 2019. Alemania pasó del 1.º puesto (2018) al 11.º tras la PPA (2020). Chile se mantiene entre el 7.º y el 10.º: un proveedor chico pero estable.  

[Ver SQL](../sql/queries/q02_supplier_ranking.sql) · 12 filas

| proveedor | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|
| España | 2 | 1 | 1 | 1 | 1,00 | 1,00 | 1 | 1 |
| Estados Unidos | 6 | 3 | 2 | 2 | 2,00 | 2,00 | 2 | 2 |
| Dinamarca | 4 | 4 | 5 | 4 | 4,00 | 6,00 | 5 | 3 |
| Brasil | 7 | 6 | 4 | 3 | 3,00 | 3,00 | 3 | 4 |
| Canadá | 3 | 7 | 3 | 6 | 6,00 | 4,00 | 4 | 5 |
| Países Bajos | 5 | 5 | 7 | 5 | 5,00 | 5,00 | 6 | 6 |
| Reino Unido | 9 | 9 | 10 | 9 | 8,00 | 9,00 | 8 | 7 |
| Francia | 8 | 8 | 9 | 7 | 7,00 | 8,00 | 7 | 8 |
| Chile | 10 | 10 | 8 | 8 | 9,00 | 7,00 | 9 | 9 |
| Irlanda | 11 | 11 | 11 | 10 | 10,00 | 10,00 | 10 | 10 |
| Alemania | 1 | 2 | 6 | 11 | 11,00 | 11,00 | 11 | 11 |
| Polonia | 12 | 12 | 12 | 12 | — | — | 12 | 12 |

## q03_yoy_growth

**Pregunta:** ¿Cuánto crecieron o cayeron las ventas de cada proveedor a China cada año?  
**Técnica:** CTE + LAG() OVER (PARTITION BY proveedor ORDER BY año) para la variación interanual  
**Fuente:** pork_gold.fact_china_imports, SOLO base espejo (lo que declaran los 12 exportadores): es la única base continua 2018–2026. Mezclar directo y espejo entre periodos sesga la comparación (ADR-008).  
**Lectura:** 2025 castiga a Brasil (−33,8%), Canadá (−28,6%) y EE. UU. (−26,8%); el Reino Unido crece (+13,0%). Casi todos caen desde 2022: China compra menos en general (ver consulta 06).  

[Ver SQL](../sql/queries/q03_yoy_growth.sql) · 12 filas

| proveedor | t_2025 | yoy_2022 | yoy_2023 | yoy_2024 | yoy_2025 |
|---|---|---|---|---|---|
| España | 502.902 | -46,5 | -12,1 | -4,7 | -5,3 |
| Estados Unidos | 353.264 | -26,5 | -7,8 | 4,0 | -26,8 |
| Dinamarca | 186.798 | -28,7 | -44,9 | -6,7 | 1,8 |
| Brasil | 159.091 | -13,5 | -15,6 | -38,1 | -33,8 |
| Canadá | 147.492 | -30,7 | 25,1 | -13,5 | -28,6 |
| Países Bajos | 146.726 | -26,4 | -19,6 | -19,5 | -13,6 |
| Reino Unido | 135.638 | -14,2 | -11,4 | 7,0 | 13,0 |
| Francia | 111.653 | -33,8 | -11,8 | -0,9 | -8,1 |
| Chile | 101.091 | -36,0 | 8,4 | -11,6 | -7,1 |
| Irlanda | 54.913 | -35,2 | -7,2 | 11,3 | -10,6 |
| Alemania | 1.294 | -90,1 | -45,0 | -37,6 | 162,7 |
| Polonia | 124 | — | — | 1.951,7 | -65,4 |

## q04_concentration_pareto

**Pregunta:** ¿Qué tan concentradas están las compras de vísceras de China? ¿Cuántos proveedores hacen el 80%?  
**Técnica:** participación acumulada con SUM() OVER (ORDER BY ... ROWS UNBOUNDED PRECEDING) + índice HHI  
**Fuente:** pork_gold.fact_china_imports, base directa (todos los orígenes), 2024 = último año completo reportado por China  
**Lectura:** 5 proveedores hacen el 77,9% de las vísceras y 6 superan el 80%. HHI ≈ 1.531: concentración moderada (umbral 1.500–2.500). Chile, el benchmark de Ecuador, es 8.º con 3,4%.  

[Ver SQL](../sql/queries/q04_concentration_pareto.sql) · 16 filas

| puesto | proveedor | toneladas | part_pct | acumulado_pct | hhi |
|---|---|---|---|---|---|
| 1 | Estados Unidos | 305.462 | 26,7 | 26,7 | 1.531 |
| 2 | España | 232.340 | 20,3 | 46,9 | 1.531 |
| 3 | Canadá | 122.088 | 10,7 | 57,6 | 1.531 |
| 4 | Países Bajos | 117.037 | 10,2 | 67,8 | 1.531 |
| 5 | Dinamarca | 115.528 | 10,1 | 77,9 | 1.531 |
| 6 | Francia | 75.812 | 6,6 | 84,5 | 1.531 |
| 7 | Reino Unido | 54.852 | 4,8 | 89,3 | 1.531 |
| 8 | Chile | 39.086 | 3,4 | 92,7 | 1.531 |
| 9 | Irlanda | 24.847 | 2,2 | 94,9 | 1.531 |
| 10 | Brasil | 21.859 | 1,9 | 96,8 | 1.531 |
| 11 | Bélgica | 11.663 | 1,0 | 97,8 | 1.531 |
| 12 | Rusia | 11.481 | 1,0 | 98,8 | 1.531 |
| 13 | Finlandia | 9.820 | 0,9 | 99,6 | 1.531 |
| 14 | Suiza | 2.943 | 0,3 | 99,9 | 1.531 |
| 15 | Portugal | 1.084 | 0,1 | 100,0 | 1.531 |
| 16 | México | 55 | 0,0 | 100,0 | 1.531 |

## q05_effective_tariff_gap

**Pregunta:** Hoy, ¿cuánto arancel paga cada proveedor en las líneas que Ecuador podría vender (SAM), y a cuántos puntos está del mejor? ¿Tiene acceso sanitario?  
**Técnica:** CTE + MIN() OVER (PARTITION BY línea) para la brecha contra el mejor + RANK()  
**Fuente:** pork_gold.fact_tariff_applied (último mes con datos de aranceles = mes actual)  
**Lectura:** Chile paga 0% en las líneas del SAM; Ecuador pagaría 9,6% con el acuerdo, mejor que Brasil (12%) y que la UE (16,9–31,8%), pero NO tiene acceso sanitario. La barrera de Ecuador no es el arancel.  

[Ver SQL](../sql/queries/q05_effective_tariff_gap.sql) · 18 filas

| hs | proveedor | acceso | efectivo_min | efectivo_max | brecha_pp | puesto |
|---|---|---|---|---|---|---|
| 020329 | Chile | sí | 0,00 | 0,00 | 0,00 | 1 |
| 020329 | Ecuador | NO | 9,60 | 9,60 | 9,60 | 2 |
| 020329 | Brasil | sí | 12,00 | 12,00 | 12,00 | 3 |
| 020329 | Alemania | sí | 16,90 | 31,80 | 16,90 | 4 |
| 020329 | Dinamarca | sí | 16,90 | 31,80 | 16,90 | 4 |
| 020329 | España | sí | 16,90 | 31,80 | 16,90 | 4 |
| 020329 | Países Bajos | sí | 16,90 | 31,80 | 16,90 | 4 |
| 020329 | Canadá | sí | 37,00 | 37,00 | 37,00 | 8 |
| 020329 | Estados Unidos | sí | 47,00 | 47,00 | 47,00 | 9 |
| 020649 | Chile | sí | 0,00 | 0,00 | 0,00 | 1 |
| 020649 | Ecuador | NO | 9,60 | 9,60 | 9,60 | 2 |
| 020649 | Brasil | sí | 12,00 | 12,00 | 12,00 | 3 |
| 020649 | Alemania | sí | 16,90 | 31,80 | 16,90 | 4 |
| 020649 | Dinamarca | sí | 16,90 | 31,80 | 16,90 | 4 |
| 020649 | España | sí | 16,90 | 31,80 | 16,90 | 4 |
| 020649 | Países Bajos | sí | 16,90 | 31,80 | 16,90 | 4 |
| 020649 | Canadá | sí | 37,00 | 37,00 | 37,00 | 8 |
| 020649 | Estados Unidos | sí | 47,00 | 47,00 | 47,00 | 9 |

## q06_china_self_sufficiency

**Pregunta:** ¿Se está cerrando la ventana de importación de China? Autosuficiencia e importaciones 2018–2027.  
**Técnica:** LAG() para variación en puntos + AVG() OVER (ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) (media móvil 3 años) + FIRST_VALUE() para comparar contra el pico de la crisis de PPA  
**Fuente:** pork_gold.fact_market_balance (USDA PSD, miles de t CWE)  
**Lectura:** las importaciones de 2027 (proyección) son el 15,5% del pico de 2020; la autosuficiencia pasa de 87,5% a 99,0%. La ventana de la PPA se cerró: el mercado para recién llegados es un nicho.  

[Ver SQL](../sql/queries/q06_china_self_sufficiency.sql) · 10 filas

| año | produccion_kt | importa_kt | autosuf_pct | cambio_pp | importa_media3 | pct_del_pico | estado |
|---|---|---|---|---|---|---|---|
| 2018 | 54.040 | 1.447 | 97,75 | — | 1.447 | 27,4 | cerrado |
| 2019 | 42.550 | 2.450 | 94,84 | -2,91 | 1.949 | 46,4 | cerrado |
| 2020 | 36.340 | 5.277 | 87,53 | -7,31 | 3.058 | 100,0 | cerrado |
| 2021 | 47.500 | 4.328 | 91,83 | 4,30 | 4.018 | 82,0 | cerrado |
| 2022 | 55.410 | 2.125 | 96,48 | 4,65 | 3.910 | 40,3 | cerrado |
| 2023 | 57.940 | 1.897 | 96,99 | 0,51 | 2.783 | 35,9 | cerrado |
| 2024 | 57.060 | 1.306 | 97,93 | 0,94 | 1.776 | 24,7 | cerrado |
| 2025 | 59.380 | 1.186 | 98,24 | 0,31 | 1.463 | 22,5 | cerrado |
| 2026 | 59.680 | 840 | 98,88 | 0,64 | 1.111 | 15,9 | proyección |
| 2027 | 58.350 | 820 | 98,95 | 0,07 | 949 | 15,5 | proyección |

## q07_seasonality

**Pregunta:** ¿En qué meses compra más China? Índice estacional para planificar embarques (vísceras y carne).  
**Técnica:** CTE + participación de cada mes en su año con SUM() OVER (PARTITION BY año), promediada entre años; índice = 100 × participación media × 12 (100 = mes promedio)  
**Fuente:** pork_gold.fact_china_imports, base espejo, 2022–2025 (años completos, después del pico de la PPA)  
**Lectura:** estacionalidad moderada (±8%). Vísceras: picos en noviembre (108), marzo (106) y octubre (105); piso en septiembre (93). Conviene que los embarques lleguen en octubre–noviembre.  

[Ver SQL](../sql/queries/q07_seasonality.sql) · 12 filas

| mes | nombre | indice_visceras | indice_carne | t_visceras_prom |
|---|---|---|---|---|
| 1 | enero | 96 | 110 | 87.763 |
| 2 | febrero | 96 | 102 | 88.314 |
| 3 | marzo | 106 | 105 | 96.764 |
| 4 | abril | 99 | 98 | 91.347 |
| 5 | mayo | 96 | 92 | 87.922 |
| 6 | junio | 101 | 97 | 92.701 |
| 7 | julio | 102 | 98 | 93.647 |
| 8 | agosto | 101 | 97 | 92.189 |
| 9 | septiembre | 93 | 94 | 85.224 |
| 10 | octubre | 105 | 103 | 95.798 |
| 11 | noviembre | 108 | 106 | 99.123 |
| 12 | diciembre | 97 | 98 | 89.069 |

## q08_fob_price_benchmark

**Pregunta:** ¿A qué precio FOB vende cada proveedor a China en las líneas del SAM? ¿Dónde queda Chile, la referencia de precio para Ecuador?  
**Técnica:** CTE + valor unitario ponderado (SUM(valor)/SUM(kg)) + PERCENT_RANK() y diferencia contra Chile con MAX(CASE ...) OVER (PARTITION BY línea)  
**Fuente:** pork_gold.fact_china_imports, base espejo (FOB: lo que cobra el exportador), 2025, sin filas marcadas como atípicas ni proveedores con menos de 500 t en la línea  
**Lectura:** Chile es el más barato en carne congelada (020329: 1,35 USD/kg FOB) y vende vísceras (020649) a 1,60 USD/kg, percentil 33, por debajo de España (1,86) y EE. UU. (1,90). Referencia de ingreso para Ecuador en el modelo financiero: ~1,60 USD/kg FOB en vísceras.  

[Ver SQL](../sql/queries/q08_fob_price_benchmark.sql) · 31 filas

| hs | proveedor | toneladas | fob_usd_kg | percentil | vs_chile |
|---|---|---|---|---|---|
| 020322 | Países Bajos | 8.525 | 2,10 | 100,00 | 0,47 |
| 020322 | España | 68.466 | 2,08 | 89,00 | 0,46 |
| 020322 | Francia | 5.138 | 1,95 | 78,00 | 0,33 |
| 020322 | Brasil | 11.274 | 1,94 | 67,00 | 0,32 |
| 020322 | Irlanda | 26.032 | 1,71 | 33,00 | 0,08 |
| 020322 | Canadá | 5.355 | 1,71 | 44,00 | 0,08 |
| 020322 | Reino Unido | 2.595 | 1,71 | 56,00 | 0,08 |
| 020322 | Estados Unidos | 2.275 | 1,66 | 22,00 | 0,04 |
| 020322 | Chile | 32.031 | 1,62 | 11,00 | 0,00 |
| 020322 | Dinamarca | 9.566 | 1,17 | 0,00 | -0,46 |
| 020329 | Alemania | 1.283 | 2,89 | 100,00 | 1,54 |
| 020329 | España | 152.713 | 2,70 | 90,00 | 1,35 |
| 020329 | Dinamarca | 46.845 | 2,44 | 80,00 | 1,09 |
| 020329 | Irlanda | 13.887 | 2,36 | 70,00 | 1,02 |
| 020329 | Estados Unidos | 100.068 | 2,23 | 60,00 | 0,88 |
| 020329 | Brasil | 126.317 | 2,21 | 50,00 | 0,86 |
| 020329 | Francia | 35.091 | 2,19 | 40,00 | 0,84 |
| 020329 | Países Bajos | 44.847 | 2,15 | 30,00 | 0,80 |
| 020329 | Reino Unido | 41.434 | 1,90 | 20,00 | 0,55 |
| 020329 | Canadá | 47.678 | 1,55 | 10,00 | 0,20 |
| 020329 | Chile | 30.966 | 1,35 | 0,00 | 0,00 |
| 020649 | Brasil | 21.491 | 2,92 | 100,00 | 1,33 |
| 020649 | Francia | 70.543 | 2,08 | 89,00 | 0,48 |
| 020649 | Países Bajos | 92.337 | 1,98 | 78,00 | 0,39 |
| 020649 | Dinamarca | 93.558 | 1,93 | 67,00 | 0,33 |
| 020649 | Estados Unidos | 245.595 | 1,90 | 56,00 | 0,31 |
| 020649 | España | 277.835 | 1,86 | 44,00 | 0,26 |
| 020649 | Chile | 38.020 | 1,60 | 33,00 | 0,00 |
| 020649 | Reino Unido | 90.161 | 1,58 | 22,00 | -0,02 |
| 020649 | Canadá | 94.396 | 1,50 | 11,00 | -0,10 |

*… y 1 filas más (ver la consulta completa).*

## q09_fifth_quarter

**Pregunta:** ¿Cuántas toneladas de vísceras vende cada país a China por cada tonelada de carne? (el "quinto cuarto": vísceras que en el mercado local valen poco y en China valen más)  
**Técnica:** pivoteo con SUM(CASE ...) + razón + RANK()  
**Fuente:** pork_gold.fact_china_imports, base espejo, 2025  
**Lectura:** Dinamarca y EE. UU. venden 2,3 t de vísceras por cada t de carne; Chile solo 0,6 y Brasil 0,16. Los proveedores lejanos de Europa/EE. UU. monetizan en China el quinto cuarto que su mercado local no paga.  

[Ver SQL](../sql/queries/q09_fifth_quarter.sql) · 11 filas

| proveedor | t_visceras | t_carne | visceras_por_t_carne | pct_visceras | musd_visceras | puesto |
|---|---|---|---|---|---|---|
| Dinamarca | 130.293 | 56.505 | 2,31 | 69,8 | 222,80 | 1 |
| Estados Unidos | 245.595 | 107.593 | 2,28 | 69,5 | 467,40 | 2 |
| Reino Unido | 90.161 | 45.477 | 1,98 | 66,5 | 142,40 | 3 |
| Canadá | 94.396 | 53.070 | 1,78 | 64,0 | 141,50 | 4 |
| Países Bajos | 93.321 | 53.379 | 1,75 | 63,6 | 185,80 | 5 |
| Francia | 70.629 | 41.021 | 1,72 | 63,3 | 147,10 | 6 |
| España | 278.304 | 222.569 | 1,25 | 55,6 | 517,20 | 7 |
| Chile | 38.094 | 62.997 | 0,60 | 37,7 | 60,70 | 8 |
| Irlanda | 14.918 | 39.995 | 0,37 | 27,2 | 19,90 | 9 |
| Brasil | 21.492 | 137.596 | 0,16 | 13,5 | 62,80 | 10 |
| Alemania | 11 | 1.283 | 0,01 | 0,9 | 0,00 | 11 |

## q10_weighted_tariff

**Pregunta:** ¿Cuánto arancel paga en promedio el cerdo que entra a China, ponderado por volumen, y cómo cambió?  
**Técnica:** unión de dos tablas de hechos por sus claves comunes + media ponderada SUM(tasa × t) / SUM(t) + LAG() para el cambio interanual en puntos  
**Fuente:** pork_gold.fact_china_imports (espejo, 12 exportadores) × pork_gold.fact_tariff_applied (arancel efectivo mínimo: NMF o acuerdo + adicionales + antidumping mínimo), 2018–2026, solo meses completos  
**Lectura:** el arancel promedio que paga la víscera que entra a China subió de 19,1% (2024) a 26,1% (2025), +7,0 pp: China sigue comprando a proveedores castigados. Un proveedor con 0–10% tendría ventaja real.  

[Ver SQL](../sql/queries/q10_weighted_tariff.sql) · 9 filas

| año | arancel_carne | arancel_visceras | cambio_visceras_pp | toneladas |
|---|---|---|---|---|
| 2018 | 13,1 | 13,4 | — | 2.030.816 |
| 2019 | 15,8 | 15,8 | 2,4 | 3.405.046 |
| 2020 | 12,4 | 15,9 | 0,1 | 5.451.785 |
| 2021 | 11,1 | 18,2 | 2,3 | 4.171.585 |
| 2022 | 14,4 | 19,3 | 1,1 | 2.844.511 |
| 2023 | 14,3 | 18,8 | -0,5 | 2.466.459 |
| 2024 | 14,8 | 19,1 | 0,3 | 2.223.912 |
| 2025 | 20,7 | 26,1 | 7,0 | 1.898.825 |
| 2026 | 20,9 | 26,1 | 0,0 | 1.082.704 |

## q11_leadership_changes

**Pregunta:** En cada línea del SAM, ¿quién es el proveedor n.º 1 hoy, desde cuándo, y cuántas veces cambió el líder?  
**Técnica:** ROW_NUMBER() para el líder de cada mes + LAG() para detectar el cambio + conteo de "rachas" (técnica gaps-and-islands)  
**Fuente:** pork_gold.fact_china_imports, base espejo, solo meses completos (mirror_coverage: en 2026-09 solo habían reportado Brasil y Chile, y Chile aparecía como líder)  
**Lectura:** el liderazgo es inestable: en vísceras (020649) cambió 34 veces desde 2018 entre solo 3 países, y EE. UU. vuelve a liderar en 2026 pese al 47%. En carne congelada con hueso (020322) España lidera desde 2022.  

[Ver SQL](../sql/queries/q11_leadership_changes.sql) · 4 filas

| hs | lider_actual | lider_desde | meses_seguidos | cambios_de_lider | lideres_distintos |
|---|---|---|---|---|---|
| 020322 | España | 2022-02 | 55 | 12 | 4 |
| 020329 | Brasil | 2026-08 | 1 | 26 | 4 |
| 020641 | Irlanda | 2026-08 | 1 | 35 | 10 |
| 020649 | Estados Unidos | 2026-07 | 2 | 34 | 3 |

## q12_sam_size

**Pregunta:** ¿De qué tamaño es el mercado que Ecuador podría atacar (SAM: carne y vísceras congeladas) y qué parte está en manos de proveedores castigados con aranceles altos (EE. UU. y Canadá)?  
**Técnica:** CTE encadenadas + agregación condicional + participación de la parte "disputable"  
**Fuente:** pork_gold.fact_china_imports, base espejo (12 exportadores, FOB), líneas is_sam, solo meses completos (2026: ene–ago y sin Francia, que no reporta desde enero)  
**Lectura:** el SAM de 2025 es 1,85 millones de t y 3.672 MUSD FOB (−14% vs 2024). El 26,8% (495 mil t) lo venden EE. UU. y Canadá con aranceles de 37–47%. Captar 1% del SAM (~18.500 t) equivale a ~8% de la producción de Ecuador (223.650 t en 2024).  

[Ver SQL](../sql/queries/q12_sam_size.sql) · 9 filas

| año | sam_t | sam_musd | fob_usd_kg | pct_eeuu_canada | t_eeuu_canada | meses |
|---|---|---|---|---|---|---|
| 2018 | 1.976.895 | 3.198,00 | 1,62 | 23,4 | 462.434 | 12 |
| 2019 | 3.130.763 | 6.985,00 | 2,23 | 19,9 | 623.878 | 12 |
| 2020 | 5.110.578 | 12.438,00 | 2,43 | 26,6 | 1.360.026 | 12 |
| 2021 | 4.017.102 | 9.865,00 | 2,46 | 23,4 | 939.624 | 12 |
| 2022 | 2.746.615 | 6.386,00 | 2,33 | 25,0 | 685.452 | 12 |
| 2023 | 2.392.570 | 5.337,00 | 2,23 | 29,0 | 694.700 | 12 |
| 2024 | 2.160.552 | 4.306,00 | 1,99 | 31,5 | 680.935 | 12 |
| 2025 | 1.851.556 | 3.672,00 | 1,98 | 26,8 | 495.367 | 12 |
| 2026 | 1.052.737 | 1.935,00 | 1,84 | 31,9 | 336.175 | 8 |
