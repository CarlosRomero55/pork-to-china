# Serie de tiempo interrumpida · vísceras de EE. UU. en China

Generado por `src/its.py`. Regresión segmentada con estacionalidad mensual y errores de Newey-West.
Corte 1 = abr-2018 (represalias 232 y 301); corte 2 = feb-2020 (Fase Uno + exclusiones de la 301).
Ene-feb 2020 se tratan como faltantes (hueco de reporte de EE. UU., supuesto #48).

## Participación de EE. UU. en el valor (pp) · PRINCIPAL

n = 138 meses · R² = 0.71 · rezagos Newey-West = 4

| término | estimado | IC 95% | p |
|---|---|---|---|
| tendencia previa (por mes) | +0.147 | [+0.009; +0.285] | 0.037 |
| salto en abr-2018 | -9.562 | [-17.603; -1.522] | 0.020 |
| cambio de pendiente desde abr-2018 (por mes) | +0.046 | [-0.349; +0.442] | 0.817 |
| salto en feb-2020 | +10.217 | [+4.307; +16.126] | 0.001 |
| cambio de pendiente desde feb-2020 (por mes) | -0.123 | [-0.542; +0.296] | 0.562 |

Efecto a 12 meses de abr-2018: -9.01 [-14.84; -3.17]

Efecto a 12 meses de feb-2020: +8.74 [-0.30; +17.79]

## Participación de EE. UU. en toneladas (pp) · robustez, desde 2016

n = 126 meses · R² = 0.60 · rezagos Newey-West = 4

| término | estimado | IC 95% | p |
|---|---|---|---|
| tendencia previa (por mes) | -0.081 | [-0.360; +0.197] | 0.565 |
| salto en abr-2018 | -10.985 | [-19.873; -2.098] | 0.016 |
| cambio de pendiente desde abr-2018 (por mes) | +0.618 | [+0.191; +1.044] | 0.005 |
| salto en feb-2020 | +4.874 | [-1.013; +10.761] | 0.104 |
| cambio de pendiente desde feb-2020 (por mes) | -0.480 | [-0.898; -0.062] | 0.025 |

Efecto a 12 meses de abr-2018: -3.58 [-11.98; +4.83]

Efecto a 12 meses de feb-2020: -0.88 [-9.82; +8.05]

## log del valor de EE. UU. con control del resto (efecto % = e^b − 1) · robustez

n = 138 meses · R² = 0.80 · rezagos Newey-West = 4

| término | estimado | IC 95% | p |
|---|---|---|---|
| tendencia previa (por mes) | +0.015 | [+0.004; +0.025] | 0.006 |
| salto en abr-2018 | -1.122 | [-2.010; -0.234] | 0.014 |
| cambio de pendiente desde abr-2018 (por mes) | +0.034 | [-0.017; +0.085] | 0.187 |
| salto en feb-2020 | +0.589 | [+0.112; +1.067] | 0.016 |
| cambio de pendiente desde feb-2020 (por mes) | -0.049 | [-0.106; +0.009] | 0.095 |
| control: log valor del resto | +0.456 | [+0.001; +0.912] | 0.050 |

Efecto a 12 meses de abr-2018: -0.71 [-1.17; -0.26] → -51% [-69%; -23%]

Efecto a 12 meses de feb-2020: +0.01 [-1.03; +1.04] → +1% [-64%; +184%]

