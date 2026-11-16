# Consultas SQL de negocio

Generado por `src/run_queries.py` el 2026-11-15 con el usuario de solo lectura `pork_bi` sobre `pork_gold`. Cada consulta está en `sql/queries/`.

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
