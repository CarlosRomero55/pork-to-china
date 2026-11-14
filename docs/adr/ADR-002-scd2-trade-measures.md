# ADR-002 · SCD tipo 2 para las medidas comerciales

- **Estado:** Aceptada
- **Fecha:** 2026-11-13

## Contexto
Los aranceles de China al cerdo cambian con frecuencia y según el socio. Ejemplos: el arancel al cerdo de EE. UU. pasó de 37% a 172% y luego a 47–57% entre 2025 y 2026; la tregua se prorrogó hasta el 10-ene-2027; la UE pasó de un antidumping provisional (sep-2025) a uno definitivo (dic-2025). Para medir el desvío de comercio y el landed cost histórico, cada mes debe cruzarse con la tasa que estaba vigente en ese mes, no con la actual.

## Decisión
`silver.trade_measures` es una dimensión de cambio lento tipo 2, con las columnas country, hs_code, measure_type, rate_pct, valid_from, valid_to, is_current y source.
- Una tasa nueva **cierra** la fila anterior (valid_to = día previo, is_current = 0) e inserta una fila nueva (valid_to = 9999-12-31, is_current = 1).
- El cruce se hace con `period BETWEEN valid_from AND valid_to`.

## Alternativas consideradas
- SCD tipo 1 (sobrescribir): descartada porque destruye el histórico.
- SCD tipo 3 (columnas "anterior" y "actual"): solo guarda un cambio; aquí hay varios.
- Tabla de eventos sin intervalos: obliga a calcular el intervalo vigente en cada consulta.

## Consecuencias
- (+) El landed cost y el desvío de comercio son correctos en cada mes histórico.
- (+) Los escenarios futuros se modelan como filas con vigencia hipotética.
- (−) Hay que validar que los intervalos no se solapen (test en la Fase 6).
