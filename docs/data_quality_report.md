# Reporte de calidad de datos · Comtrade (bronze → silver)

_Generado automáticamente por `src/validate.py` el 2026-11-15 13:03. No editar a mano._

## 1. Antes vs después

| Etapa | Filas |
|---|---:|
| Registros en bronze (última versión de cada consulta) | 11.066 |
| Descartados por no ser totales (desgloses) | 0 |
| En cuarentena (país desconocido) | 0 |
| Cargados en silver | 11.066 |
| De ellos, con alguna marca de calidad | 280 |

Ninguna fila se borra: las dudosas se **marcan** en `quality_flag` y gold decide cómo usarlas.

| Marca en silver | Filas |
|---|---:|
| `outlier_unit_value` | 152 |
| `missing_weight` | 5 |
| `weight_estimated_by_source` | 128 |
| `sin_marca` | 10.786 |

## 2. Reglas de calidad

| Regla | Descripción | Estado | Filas afectadas | Detalle |
|---|---|---|---:|---|
| R01 | Completitud bronze → silver | ✅ OK | 0 | bronze 11.066 = silver 11.066 + cuarentena 0 |
| R02 | Países fuera del catálogo (cuarentena) | ✅ OK | 0 | todas las filas tienen país conocido |
| R03 | Suma de socios ≤ total Mundo (China, peso) | ✅ OK | 0 | 576 combinaciones HS×mes revisadas |
| R04 | Serie mensual sin huecos | ✅ OK | 0 | comtrade: 2018-01 a 2024-12; comtrade_mirror: 2018-01 a 2026-09 |
| R05 | USD/kg fuera de rango plausible → marcado como atípico | ✅ OK | 0 | 43 filas fuera de rango (0,42% de 10.341 ≥ 1 t), 43 marcadas · carne 0,5–15 · vísceras 0,3–10 · procesado 0,5–100 USD/kg |
| R06 | Filas sin peso ≤ 1% | ✅ OK | 5 | 0,045% de 11.066 filas |
| R07 | Espejo vs directo en peso (±10%, 2018–2024) | ✅ OK | 0 | BRA 1,005 · CAN 0,956 · CHL 0,993 · DEU 1,038 · DNK 0,994 · ESP 1,015 · FRA 1,021 · GBR 0,979 · IRL 0,977 · NLD 0,995 · USA 0,936 |
| R08 | Picos mensuales > 3× la mediana | ⚠️ ALERTA | 19 | comtrade/0203/2020-07, comtrade/0203/2020-12, comtrade/0203/2021-03, comtrade/0203/2021-04 |
| R09 | Sin periodos en el futuro | ✅ OK | 0 | último periodo 2026-09 |
| R10 | Medidas arancelarias sin vigencias solapadas (SCD2) | ✅ OK | 0 | cada medida tiene una sola tasa vigente por fecha |
| R11 | Marcas de calidad coherentes con los datos | ✅ OK | 0 | quality_flag = missing_weight ⇔ peso NULL |

### Interpretación de las alertas

- **R08 · Picos mensuales > 3× la mediana:** Los picos se concentran en 2020–2021: la peste porcina africana redujo la piara china y las importaciones llegaron a un récord (~4,3 Mt en 2020). Son datos reales, no errores; por eso las comparaciones de 2025 se hacen contra 2024 y no contra el promedio histórico.

### Hallazgos de la revisión de valores unitarios

- **España, HS 020312 (piernas frescas con hueso), 2018:** 0,27–0,48 USD/kg, imposible para ese producto. Probable error de clasificación del exportador (huesos o patas declarados como piernas). Marcadas.
- **Reino Unido y Francia, envíos de 1,3–1,9 t a 15–25 USD/kg:** muestras o envíos aéreos, no comercio representativo. Marcadas.
- La regla estadística (IQR por HS × año) no detectaba los casos de España porque el error se repite todo el año y se parece a sí mismo; por eso se combina con un rango plausible de negocio.
- Las filas marcadas se excluyen del cálculo de precios promedio en gold, pero sí cuentan en volumen.

## 3. Cobertura por fuente y año (filas)

| año | comtrade | comtrade_mirror |
|---|---|---|
| 2.018 | 649 | 676 |
| 2.019 | 659 | 801 |
| 2.020 | 892 | 877 |
| 2.021 | 816 | 750 |
| 2.022 | 669 | 701 |
| 2.023 | 641 | 675 |
| 2.024 | 673 | 644 |
| 2.025 | 0 | 589 |
| 2.026 | 0 | 354 |

## 4. Conciliación espejo vs directo (peso, 2018–2024)

Ratio = toneladas que China dice haber importado ÷ toneladas que el exportador dice haberle vendido.

| país | china_t | exportador_t | ratio |
|---|---|---|---|
| ESP | 5.244.085 | 5.166.975 | 1,015 |
| USA | 3.545.484 | 3.788.725 | 0,936 |
| BRA | 2.552.117 | 2.540.344 | 1,005 |
| DNK | 2.302.178 | 2.316.888 | 0,994 |
| CAN | 1.952.561 | 2.043.222 | 0,956 |
| NLD | 1.912.010 | 1.922.319 | 0,995 |
| DEU | 1.481.981 | 1.428.135 | 1,038 |
| FRA | 1.100.080 | 1.077.518 | 1,021 |
| CHL | 917.703 | 924.584 | 0,993 |
| GBR | 876.645 | 895.723 | 0,979 |
| IRL | 494.145 | 505.563 | 0,977 |

## 5. Valores unitarios fuera de rango (muestra)

| source | reporter | partner | hs_code | period | net_weight_kg | usd_kg |
|---|---|---|---|---|---|---|
| comtrade_mirror | CAN | CHN | 020319 | 2022-02 | 1.175.576 | 0,480 |
| comtrade | CHN | DNK | 020322 | 2024-04 | 244.366 | 0,470 |
| comtrade | CHN | DNK | 020322 | 2024-03 | 222.106 | 0,450 |
| comtrade_mirror | ESP | CHN | 020312 | 2023-08 | 5.084,430 | 19,110 |
| comtrade_mirror | CHL | CHN | 020641 | 2019-04 | 336.165,390 | 0,280 |
| comtrade_mirror | ESP | CHN | 020312 | 2018-11 | 157.340 | 0,480 |
| comtrade_mirror | ESP | CHN | 020312 | 2018-09 | 169.179 | 0,350 |
| comtrade_mirror | ESP | CHN | 020312 | 2018-10 | 151.130 | 0,390 |
| comtrade_mirror | ESP | CHN | 020312 | 2019-02 | 114.430 | 0,500 |
| comtrade_mirror | ESP | CHN | 020321 | 2023-09 | 1.856,580 | 23,800 |

## 6. Limitaciones conocidas

- China no ha publicado en Comtrade sus importaciones mensuales de 2025–2026: ese periodo se cubre con datos espejo (ADR-008). Los valores espejo son FOB; los de China, CIF (factor de conciliación ≈ 1,037).
- Los 12 exportadores del espejo concentran la gran mayoría del volumen; los demás no aparecen en 2025–2026.
- Comtrade revisa datos con meses de atraso: los 2 últimos años se vuelven a descargar en cada corrida.
