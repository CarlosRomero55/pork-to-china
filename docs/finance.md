# Flujo de caja, VAN y TIR de AgroPorc por escenario

Generado por `src/finance.py`. USD reales; año 0 = 2026; tasa de descuento 12%; impuesto efectivo 36,25%. Supuestos en `silver.assumption` (ver `docs/assumptions.md`).

Inversión base: 555,000 USD · margen variable: -0,03 USD/kg

**víscera_máx**: valor local máximo de la víscera con el que el proyecto todavía tiene VAN = 0. Si en Ecuador la víscera vale menos que eso, exportar conviene.  
**t_equilibrio**: toneladas anuales (con la rampa 40-70-100) necesarias para VAN = 0 si el mercado no limitara.

| escenario | VAN_kUSD | TIR_% | payback | víscera_máx | t_equilibrio | divisas_MUSD | empleos |
|---|---|---|---|---|---|---|---|
| A-up-NA | -555 | — | — | — | — | 0,00 | 0,00 |
| A-down-NA | -555 | — | — | — | — | 0,00 | 0,00 |
| C-down-NA | -555 | — | — | — | — | 0,00 | 0,00 |
| C-up-NA | -555 | — | — | — | — | 0,00 | 0,00 |
| B-down-NA | -555 | — | — | — | — | 0,00 | 0,00 |
| B-up-NA | -555 | — | — | — | — | 0,00 | 0,00 |
| A-up-6 | -987 | -32,16 | — | 1,08 | — | 16,20 | 14,00 |
| B-up-6 | -1.071 | -27,22 | — | 1,14 | — | 22,80 | 18,00 |
| A-down-6 | -1.078 | -27,32 | — | 1,15 | — | 23,70 | 18,00 |
| B-down-6 | -1.178 | -24,39 | — | 1,19 | — | 32,10 | 23,00 |
| C-up-6 | -1.186 | -23,92 | — | 1,19 | — | 32,60 | 23,00 |
| C-down-6 | -1.187 | -24,02 | — | 1,19 | — | 32,80 | 23,00 |
| A-up-4 | -1.265 | -30,45 | — | 1,15 | — | 23,40 | 15,00 |
| A-down-4 | -1.399 | -25,78 | — | 1,20 | — | 33,00 | 18,00 |
| B-up-4 | -1.420 | -25,23 | — | 1,20 | — | 33,50 | 18,00 |
| B-down-4 | -1.593 | -22,27 | — | 1,23 | — | 46,60 | 23,00 |
| A-up-2 | -1.624 | -29,62 | — | 1,20 | — | 31,00 | 15,00 |
| C-up-4 | -1.629 | -21,59 | — | 1,23 | — | 48,60 | 23,00 |
| C-down-4 | -1.630 | -21,67 | — | 1,23 | — | 48,80 | 23,00 |
| A-down-2 | -1.788 | -25,18 | — | 1,22 | — | 41,80 | 18,00 |
| B-up-2 | -1.869 | -24,29 | — | 1,23 | — | 44,70 | 19,00 |
| B-down-2 | -2.096 | -21,45 | — | 1,25 | — | 60,20 | 23,00 |
| C-up-2 | -2.184 | -20,60 | — | 1,25 | — | 64,60 | 23,00 |
| C-down-2 | -2.185 | -20,67 | — | 1,25 | — | 64,80 | 23,00 |

Escenarios con VAN positivo: 0 de 24.
