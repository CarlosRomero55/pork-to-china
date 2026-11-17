# ADR-011 · Serie de tiempo interrumpida para medir el efecto de la guerra comercial

**Fecha:** 2026-11-17 · **Estado:** aceptada · **Fase:** 14.2

## Contexto
Queremos saber si las represalias de China de 2018 y el acuerdo Fase Uno de 2020 cambiaron la posición de
EE. UU. en las vísceras de cerdo que compra China, separando ese efecto de la tendencia, la estacionalidad y la
peste porcina africana (PPA, ago-2018), que subió la demanda china al mismo tiempo.

## Decisiones
1. **Regresión segmentada (ITS)** con dos cortes (abr-2018 y feb-2020), 11 dummies de mes y tendencia.
2. **Medida principal: participación de EE. UU. en el valor.** La participación neutraliza la PPA (afectó a
   todos los proveedores); el valor evita el problema del peso, que EE. UU. no reportó en 2015 y estimó en 2016-17.
3. **Robustez:** participación en toneladas (desde 2016) y log del valor de EE. UU. con el log del resto como control.
4. **Datos 2015-2017** (6 consultas nuevas a Comtrade, decisión de Carlos): viven en silver y **no entran a gold**;
   `build_gold.read_flows` filtra desde `START_YEAR` (2018). El resto del modelo no cambia.
5. **Ene-feb 2020 como faltantes** (hueco de reporte de EE. UU., supuesto #48).
6. **Errores de Newey-West** implementados con NumPy (sin dependencias nuevas como statsmodels).
7. **Sección 301 en el modelo** (migración 019, supuesto #47): +25% del 6-jul-2018 al 1-mar-2020.

## Consecuencias
- Resultado principal: −9,6 pp en abr-2018 (p = 0,02) y +10,2 pp en feb-2020 (p = 0,001); el modelo en log lo
  confirma y en toneladas el salto de 2018 se confirma pero el de 2020 no es significativo.
- Limitaciones: 39 meses antes del primer corte; cortes cercanos a la PPA; la escalada de abril de 2025 no es corte.
