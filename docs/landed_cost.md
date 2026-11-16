# Costo puesto en China (landed cost)

Generado por `src/landed_cost.py`. USD por kg, sin IVA (igual para todos). FOB real 2025 (espejo); arancel efectivo vigente; flete, carga y seguro según `silver.assumption` (mín · base · máx).

## Vísceras congeladas (020649)

| proveedor | acceso | fob | flete | seguro | cif | arancel_pct | landed_min | landed_max | vs_mejor |
|---|---|---|---|---|---|---|---|---|---|
| Chile | sí | 1,6 | 0,188 | 0,005 | 1,79 | 0 | 1,79 | 1,79 | 0 |
| Ecuador (con acuerdo) | NO | 1,6 | 0,188 | 0,005 | 1,79 | 9,6 | 1,96 | 1,96 | 0,17 |
| Ecuador (NMF) | NO | 1,6 | 0,188 | 0,005 | 1,79 | 12 | 2 | 2 | 0,21 |
| Canadá | sí | 1,5 | 0,146 | 0,005 | 1,65 | 37 | 2,26 | 2,26 | 0,47 |
| España | sí | 1,86 | 0,179 | 0,006 | 2,04 | 16,9–31,8 | 2,39 | 2,69 | 0,6 |
| Dinamarca | sí | 1,93 | 0,179 | 0,006 | 2,12 | 16,9–31,8 | 2,47 | 2,79 | 0,68 |
| Estados Unidos | sí | 1,9 | 0,146 | 0,006 | 2,06 | 47 | 3,02 | 3,02 | 1,23 |
| Brasil | sí | 2,92 | 0,229 | 0,009 | 3,16 | 12 | 3,54 | 3,54 | 1,75 |

## Carne congelada (020329)

| proveedor | acceso | fob | flete | seguro | cif | arancel_pct | landed_min | landed_max | vs_mejor |
|---|---|---|---|---|---|---|---|---|---|
| Chile | sí | 1,35 | 0,188 | 0,005 | 1,54 | 0 | 1,54 | 1,54 | 0 |
| Ecuador (con acuerdo) | NO | 1,35 | 0,188 | 0,005 | 1,54 | 9,6 | 1,69 | 1,69 | 0,15 |
| Ecuador (NMF) | NO | 1,35 | 0,188 | 0,005 | 1,54 | 12 | 1,72 | 1,72 | 0,18 |
| Canadá | sí | 1,55 | 0,146 | 0,005 | 1,7 | 37 | 2,33 | 2,33 | 0,79 |
| Brasil | sí | 2,21 | 0,229 | 0,007 | 2,45 | 12 | 2,74 | 2,74 | 1,2 |
| Dinamarca | sí | 2,44 | 0,179 | 0,008 | 2,63 | 16,9–31,8 | 3,07 | 3,46 | 1,53 |
| España | sí | 2,7 | 0,179 | 0,009 | 2,89 | 16,9–31,8 | 3,38 | 3,81 | 1,84 |
| Estados Unidos | sí | 2,23 | 0,146 | 0,007 | 2,38 | 47 | 3,5 | 3,5 | 1,96 |

## FOB máximo de Ecuador para igualar en destino (020649, con acuerdo)

| competidor | landed_competidor | fob_max_flete_bajo | fob_max_base | fob_max_flete_alto |
|---|---|---|---|---|
| Chile | 1,79 | 1,51 | 1,44 | 1,25 |
| Canadá | 2,26 | 1,94 | 1,87 | 1,68 |
| España | 2,39 | 2,06 | 1,99 | 1,79 |
| Dinamarca | 2,47 | 2,13 | 2,06 | 1,87 |
| Estados Unidos | 3,02 | 2,63 | 2,56 | 2,37 |
| Brasil | 3,54 | 3,11 | 3,03 | 2,84 |

## Sensibilidad al flete (020649)

| proveedor | puesto_min | landed_min | puesto_base | landed_base | puesto_max | landed_max |
|---|---|---|---|---|---|---|
| Chile | 1 | 1,71 | 1 | 1,79 | 1 | 1,98 |
| Ecuador (con acuerdo) | 2 | 1,88 | 2 | 1,96 | 2 | 2,17 |
| Ecuador (NMF) | 3 | 1,92 | 3 | 2 | 3 | 2,22 |
| Canadá | 4 | 2,16 | 4 | 2,26 | 4 | 2,41 |
| España | 5 | 2,29 | 5 | 2,39 | 5 | 2,51 |
| Dinamarca | 6 | 2,37 | 6 | 2,47 | 6 | 2,6 |
| Estados Unidos | 7 | 2,92 | 7 | 3,02 | 7 | 3,18 |
| Brasil | 8 | 3,43 | 8 | 3,54 | 8 | 3,74 |

El orden de proveedores no cambia con el flete en su mínimo o máximo.
