# Flujo de caja, VAN y TIR de AgroPorc por escenario

Generado por `src/finance.py`. USD reales; año 0 = 2026; tasa de descuento 12%; impuesto efectivo 36,25%. Supuestos en `silver.assumption` (ver `docs/assumptions.md`).

Inversión base: 555,000 USD · margen variable: 0,45 USD/kg

**víscera_máx**: valor local máximo de la víscera con el que el proyecto todavía tiene VAN = 0. Si en Ecuador la víscera vale menos que eso, exportar conviene.  
**t_equilibrio**: toneladas anuales (con la rampa 40-70-100) necesarias para VAN = 0 si el mercado no limitara.

| escenario | VAN_kUSD | TIR_% | payback | víscera_máx | t_equilibrio | divisas_MUSD | empleos |
|---|---|---|---|---|---|---|---|
| C-down-2 | 4.685 | 69,84 | 2,61 | 1,25 | 707 | 64,80 | 23,00 |
| C-up-2 | 4.672 | 69,83 | 2,61 | 1,25 | 707 | 64,60 | 23,00 |
| B-down-2 | 4.280 | 67,17 | 2,61 | 1,25 | 707 | 60,20 | 23,00 |
| B-up-2 | 3.156 | 62,38 | 2,61 | 1,23 | 707 | 44,70 | 19,00 |
| C-down-4 | 2.928 | 44,32 | 4,61 | 1,23 | 961 | 48,80 | 23,00 |
| C-up-4 | 2.915 | 44,29 | 4,61 | 1,23 | 961 | 48,60 | 23,00 |
| A-down-2 | 2.814 | 57,26 | 2,68 | 1,22 | 707 | 41,80 | 18,00 |
| B-down-4 | 2.761 | 43,33 | 4,61 | 1,23 | 961 | 46,60 | 23,00 |
| A-up-2 | 2.005 | 51,53 | 2,72 | 1,20 | 707 | 31,00 | 15,00 |
| B-up-4 | 1.879 | 38,44 | 4,62 | 1,20 | 961 | 33,50 | 18,00 |
| A-down-4 | 1.805 | 37,31 | 4,66 | 1,20 | 961 | 33,00 | 18,00 |
| C-down-6 | 1.527 | 30,53 | 6,61 | 1,19 | 1.483 | 32,80 | 23,00 |
| C-up-6 | 1.515 | 30,45 | 6,61 | 1,19 | 1.483 | 32,60 | 23,00 |
| B-down-6 | 1.484 | 30,22 | 6,61 | 1,19 | 1.483 | 32,10 | 23,00 |
| A-up-4 | 1.133 | 31,65 | 4,73 | 1,15 | 961 | 23,40 | 15,00 |
| A-down-6 | 953 | 26,01 | 6,65 | 1,15 | 1.483 | 23,70 | 18,00 |
| B-up-6 | 904 | 25,62 | 6,63 | 1,14 | 1.483 | 22,80 | 18,00 |
| A-up-6 | 478 | 20,69 | 6,75 | 1,08 | 1.483 | 16,20 | 14,00 |
| C-up-NA | -555 | — | — | — | — | 0,00 | 0,00 |
| C-down-NA | -555 | — | — | — | — | 0,00 | 0,00 |
| B-up-NA | -555 | — | — | — | — | 0,00 | 0,00 |
| B-down-NA | -555 | — | — | — | — | 0,00 | 0,00 |
| A-up-NA | -555 | — | — | — | — | 0,00 | 0,00 |
| A-down-NA | -555 | — | — | — | — | 0,00 | 0,00 |

Escenarios con VAN positivo: 18 de 24.
