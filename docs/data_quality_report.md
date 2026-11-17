# Reporte de calidad de datos · Comtrade y USDA PSD (bronze → silver)

_Generado automáticamente por `src/validate.py` el 2026-11-17 17:43. No editar a mano._

## 1. Antes vs después

| Etapa | Filas |
|---|---:|
| Registros en bronze (última versión de cada consulta) | 14.467 |
| Descartados por no ser totales (desgloses) | 0 |
| En cuarentena (país desconocido) | 0 |
| Cargados en silver | 14.467 |
| De ellos, con alguna marca de calidad | 1.921 |

Ninguna fila se borra: las dudosas se **marcan** en `quality_flag` y gold decide cómo usarlas.

| Marca en silver | Filas |
|---|---:|
| `outlier_unit_value` | 300 |
| `missing_weight` | 58 |
| `weight_estimated_by_source` | 1.568 |
| `sin_marca` | 12.546 |

## 2. Reglas de calidad

| Regla | Descripción | Estado | Filas afectadas | Detalle |
|---|---|---|---:|---|
| R01 | Completitud bronze → silver | ✅ OK | 0 | bronze 14.467 = silver 14.467 + cuarentena 0 |
| R02 | Países fuera del catálogo (cuarentena) | ✅ OK | 0 | todas las filas tienen país conocido |
| R03 | Suma de socios ≤ total Mundo (China, peso) | ✅ OK | 0 | 730 combinaciones HS×mes revisadas |
| R04 | Serie mensual sin huecos | ✅ OK | 0 | comtrade: 2016-01 a 2024-12; comtrade_mirror: 2015-01 a 2026-09 |
| R05 | USD/kg fuera de rango plausible → marcado como atípico | ✅ OK | 0 | 55 filas fuera de rango (0,40% de 13.589 ≥ 1 t), 55 marcadas · carne 0,5–15 · vísceras 0,3–10 · procesado 0,5–100 USD/kg |
| R06 | Filas sin peso ≤ 1% | ✅ OK | 58 | 0,401% de 14.467 filas |
| R07 | Espejo vs directo en peso (±10%, 2018–2024) | ⚠️ ALERTA | 5 | BRA 0,998 · CAN 0,899 · CHL 0,934 · DEU 0,883 · DNK 0,966 · ESP 0,983 · FRA 0,992 · GBR 0,898 · IRL 0,885 · NLD 0,954 · USA 1,176 |
| R08 | Picos mensuales > 3× la mediana | ⚠️ ALERTA | 42 | comtrade/0203/2020-03, comtrade/0203/2020-04, comtrade/0203/2020-06, comtrade/0203/2020-07 |
| R09 | Sin periodos en el futuro | ✅ OK | 0 | último periodo 2026-09 |
| R10 | Medidas arancelarias sin vigencias solapadas (SCD2) | ✅ OK | 0 | cada medida tiene una sola tasa vigente por fecha |
| R11 | Marcas de calidad coherentes con los datos | ✅ OK | 0 | quality_flag = missing_weight ⇔ peso NULL |
| R12 | USDA: oferta = demanda en cada balance | ⚠️ ALERTA | 1 | 316 balances país×año revisados (±0,5%) · ej.: BO 2023 |

### Interpretación de las alertas

- **R07 · Espejo vs directo en peso (±10%, 2018–2024):** Un exportador grande con más de 10% de diferencia entre su dato y el de China: revisar tránsito por terceros países (por ejemplo, Hong Kong) o desfase de fechas antes de usar su espejo.
- **R08 · Picos mensuales > 3× la mediana:** Los picos se concentran en 2020–2021: la peste porcina africana redujo la piara china y las importaciones llegaron a un récord (~4,3 Mt en 2020). Son datos reales, no errores; por eso las comparaciones de 2025 se hacen contra 2024 y no contra el promedio histórico.
- **R12 · USDA: oferta = demanda en cada balance:** Algún balance de USDA no cierra en la propia fuente (p. ej. Bielorrusia 2023: producción + importaciones = 395 mil t frente a una oferta total publicada de 377). Son inconsistencias de USDA, no del proceso; no afectan el análisis si el país no es proveedor de China ni competidor de Ecuador.

### Hallazgos de la revisión de valores unitarios

- **España, HS 020312 (piernas frescas con hueso), 2018:** 0,27–0,48 USD/kg, imposible para ese producto. Probable error de clasificación del exportador (huesos o patas declarados como piernas). Marcadas.
- **Reino Unido y Francia, envíos de 1,3–1,9 t a 15–25 USD/kg:** muestras o envíos aéreos, no comercio representativo. Marcadas.
- La regla estadística (IQR por HS × año) no detectaba los casos de España porque el error se repite todo el año y se parece a sí mismo; por eso se combina con un rango plausible de negocio.
- Las filas marcadas se excluyen del cálculo de precios promedio en gold, pero sí cuentan en volumen.

## 3. Cobertura por fuente y año (filas)

| año | comtrade | comtrade_mirror |
|---|---|---|
| 2.015 | 0 | 658 |
| 2.016 | 713 | 702 |
| 2.017 | 679 | 649 |
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
| ESP | 5.948.573 | 6.049.818 | 0,983 |
| USA | 5.268.942 | 4.481.905 | 1,176 |
| DNK | 2.961.279 | 3.065.487 | 0,966 |
| BRA | 2.677.106 | 2.682.099 | 0,998 |
| CAN | 2.514.081 | 2.796.357 | 0,899 |
| DEU | 2.383.622 | 2.700.370 | 0,883 |
| NLD | 2.324.832 | 2.436.855 | 0,954 |
| FRA | 1.409.265 | 1.420.339 | 0,992 |
| CHL | 1.048.602 | 1.122.649 | 0,934 |
| GBR | 987.511 | 1.099.107 | 0,898 |
| IRL | 612.867 | 692.435 | 0,885 |

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
| comtrade_mirror | GBR | CHN | 020319 | 2017-08 | 119.410 | 0,470 |

## 6. Limitaciones conocidas

- China no ha publicado en Comtrade sus importaciones mensuales de 2025–2026: ese periodo se cubre con datos espejo (ADR-008). Los valores espejo son FOB; los de China, CIF (factor de conciliación ≈ 1,037).
- Los 12 exportadores del espejo concentran la gran mayoría del volumen; los demás no aparecen en 2025–2026.
- Comtrade revisa datos con meses de atraso: los 2 últimos años se vuelven a descargar en cada corrida.
