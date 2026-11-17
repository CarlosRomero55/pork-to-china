# Monte Carlo del VAN de AgroPorc

Generado por `src/monte_carlo.py`: 10.000 sorteos triangulares (mín–base–máx) de 12 supuestos de costo, precio y capacidad; semilla 2026; los mismos sorteos en los 24 escenarios. Tasa de descuento fija en 12%. Supuestos independientes entre sí.

**Probabilidad de VAN positivo en los escenarios con certificación:** de 1% a 11% (mediana 6%). Sin certificación: 0%.

| escenario | P(VAN > 0) | VAN p5 (M USD) | VAN mediana | VAN p95 | VAN con valores base |
|---|---|---|---|---|---|
| C-down-2 | 11.3% | -15.46 | -4.86 | +1.02 | -2.19 |
| C-up-2 | 10.9% | -14.55 | -4.70 | +0.92 | -2.18 |
| B-down-2 | 10.4% | -13.24 | -4.40 | +0.79 | -2.10 |
| C-down-4 | 9.2% | -10.45 | -3.41 | +0.49 | -1.63 |
| C-up-4 | 8.7% | -9.75 | -3.30 | +0.41 | -1.63 |
| B-up-2 | 8.6% | -10.68 | -3.73 | +0.46 | -1.87 |
| B-down-4 | 8.4% | -9.24 | -3.18 | +0.36 | -1.59 |
| A-down-2 | 8.0% | -9.86 | -3.50 | +0.36 | -1.79 |
| B-up-4 | 6.0% | -7.18 | -2.66 | +0.10 | -1.42 |
| A-down-4 | 5.9% | -7.05 | -2.61 | +0.08 | -1.40 |
| A-up-2 | 5.8% | -7.90 | -2.96 | +0.09 | -1.62 |
| C-down-6 | 5.7% | -6.45 | -2.27 | +0.07 | -1.19 |
| C-up-6 | 5.1% | -6.01 | -2.19 | +0.02 | -1.19 |
| B-down-6 | 5.1% | -5.90 | -2.17 | +0.00 | -1.18 |
| A-up-4 | 3.3% | -5.41 | -2.16 | -0.14 | -1.26 |
| A-down-6 | 2.9% | -4.67 | -1.86 | -0.16 | -1.08 |
| B-up-6 | 2.6% | -4.55 | -1.83 | -0.17 | -1.07 |
| A-up-6 | 0.7% | -3.52 | -1.55 | -0.32 | -0.99 |
| C-up-NA | 0.0% | -0.70 | -0.59 | -0.50 | -0.56 |
| C-down-NA | 0.0% | -0.70 | -0.59 | -0.50 | -0.56 |
| B-up-NA | 0.0% | -0.70 | -0.59 | -0.50 | -0.56 |
| B-down-NA | 0.0% | -0.70 | -0.59 | -0.50 | -0.56 |
| A-up-NA | 0.0% | -0.70 | -0.59 | -0.50 | -0.56 |
| A-down-NA | 0.0% | -0.70 | -0.59 | -0.50 | -0.56 |

## Qué supuesto pesa más (escenario B-up-4)

| supuesto | VAN con el mínimo (M USD) | VAN con el máximo | rango | Spearman |
|---|---|---|---|---|
| Valor local de la víscera | +0.37 | -9.42 | 9.79 | -0.94 |
| Precio FOB de exportación | -2.38 | +0.46 | 2.84 | +0.28 |
| Costo de proceso | -0.93 | -1.91 | 0.98 | -0.09 |
| Costo de congelación | -1.22 | -1.71 | 0.49 | -0.04 |
| Logística de exportación | -1.22 | -1.61 | 0.39 | -0.03 |
| Costo fijo anual | -1.29 | -1.58 | 0.29 | -0.04 |
| Capital de trabajo (meses) | -1.29 | -1.55 | 0.25 | -0.03 |
| Inversión: adecuación de planta | -1.32 | -1.57 | 0.25 | -0.01 |
| Inversión: habilitación para China | -1.37 | -1.52 | 0.15 | -0.02 |
| Capacidad de la planta | -1.33 | -1.46 | 0.14 | -0.03 |
| Inversión: túnel de congelación | -1.40 | -1.47 | 0.07 | -0.01 |
| Inversión: cámara de frío | -1.40 | -1.43 | 0.04 | -0.00 |
