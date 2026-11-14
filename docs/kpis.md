# KPIs del proyecto

Convenciones: toneladas métricas (t), USD nominales, periodo mensual. Ventana de comparación: 12 meses antes / 12 meses después de cada corte.
Cortes: 2025-03 (EE. UU.), 2025-09 (UE provisional), 2025-12 (UE definitivo).

| # | Pregunta | KPI | Fórmula | Grano | Tabla gold |
|---|---|---|---|---|---|
| 1 | P1 Ventana | `share_pct` | t(socio, HS, mes) / t(total, HS, mes) × 100 | socio–HS–mes | fact_china_imports |
| 2 | P1 | `share_change_pp` | share promedio post 12m − share promedio pre 12m | socio–HS–corte | vista sobre fact_china_imports |
| 3 | P1 | `diverted_tonnes` | sancionados: vol_pre − vol_post; ganadores: vol_post − vol_pre; lo que pierden los sancionados contra lo que ganan los demás = redistribuido vs desaparecido | socio–HS–corte | fact_china_imports |
| 4 | P1 | `unit_value_usd_kg` | value_usd / net_weight_kg | socio–HS–mes | fact_china_imports |
| 5 | P1 | TAM / SAM / SOM | TAM = importaciones de 0203+0206+0210; SAM = líneas congeladas que Ecuador puede ofrecer (020322, 020329, 020641, 020649); SOM = SAM × achievable_share | HS–año | fact_china_imports + silver.assumptions |
| 6 | P2 Competitividad | `landed_cost_usd_kg` | CIF = FOB + flete + seguro; landed = CIF × (1 + NMF/preferencial + adicional + antidumping) | proveedor–producto–escenario | fact_landed_cost |
| 7 | P2 | `gap_vs_best` | landed(Ecuador) − mín(landed de los demás), en USD/kg y en % | producto–escenario | fact_landed_cost |
| 8 | P3 Factibilidad | `regulatory_gap` | requisitos cumplidos / requisitos totales, más el costo y los años de los faltantes | requisito | silver.assumptions + benchmark |
| 9 | P4 Costo-beneficio | `npv` | Σ FC_t / (1+r)^t − I0, con t = 1…10 | escenario | fact_scenario_cashflow |
| 10 | P4 | `irr` | r tal que VAN = 0 | escenario | fact_scenario_cashflow |
| 11 | P4 | `payback_years` | primer t con FC acumulado ≥ 0 (simple y descontado) | escenario | fact_scenario_cashflow |
| 12 | P4 | `breakeven_tonnes` | (anualidad(I0) + costos fijos) / (precio CIF neto − costo variable por t) | escenario | fact_scenario_cashflow |
| 13 | P5 Riesgo/país | divisas, empleo, P(VAN>0) | divisas = t × FOB; empleo = t × jobs_per_tonne; P = n(VAN>0) / 10.000 | escenario | fact_scenario_cashflow, fact_monte_carlo |

Notas:
- China cobra los aranceles sobre el valor CIF.
- El IVA de importación (9%) se excluye de la comparación porque aplica igual a todos los proveedores.

## Árbol pregunta → KPI → gold
```
P1 Ventana         → KPI 1–5  → fact_china_imports
P2 Competitividad  → KPI 6–7  → fact_landed_cost
P3 Factibilidad    → KPI 8    → silver.assumptions + benchmark
P4 Costo-beneficio → KPI 9–12 → fact_scenario_cashflow
P5 Riesgo/país     → KPI 13   → fact_scenario_cashflow + fact_monte_carlo
```
