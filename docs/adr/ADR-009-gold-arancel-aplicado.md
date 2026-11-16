# ADR-009 · Gold: reconstrucción completa y arancel aplicado precalculado

- **Estado:** Aceptada
- **Fecha:** 2026-11-15

## Contexto
El tablero (Streamlit) y el simulador necesitan saber, para cualquier mes, origen y línea HS,
cuánto arancel paga el cerdo al entrar a China. En silver eso está repartido en medidas SCD2
(NMF, represalias, antidumping por empresa, acuerdos), con vigencias que cambian a mitad de mes.

## Decisiones
1. **Gold se reconstruye completo en cada corrida** (vaciar y llenar en una transacción).
   Son ~110 mil filas y tarda ~20 s; gold nunca se desincroniza de silver. La carga
   incremental se justificaría con millones de filas.
2. **`fact_tariff_applied` precalculada** (mes × origen × línea): 180 meses × 47 orígenes × 12 líneas.
   - Tasa vigente **el día 15** de cada mes (convención documentada).
   - Medidas a bloques (UE) se expanden según la **fecha de pertenencia** (el Reino Unido deja de
     recibir el antidumping de la UE).
   - Tasas por empresa (antidumping) se guardan como **rango mín–máx**, nunca se suman.
   - Un acuerdo comercial **reemplaza** al NMF (`effective_*`); no se suma.
3. **Directo y espejo son filas distintas** en `fact_china_imports` (columna `basis`), nunca se
   mezclan. La vista `v_supplier_tonnes` arma una serie continua **solo en toneladas**
   (directo hasta 2024-12, espejo desde 2025-01), porque en valor uno es CIF y el otro FOB.
4. **Acceso sanitario observado en los datos** (`dim_country.exports_pork_to_china`): el país
   le vendió cerdo a China en los últimos 24 meses con datos de su base. Un arancel bajo no sirve
   sin acceso: es el caso de Ecuador.

## Consecuencias
- (+) Consultas del tablero simples y rápidas; la lógica arancelaria vive en un solo lugar y está probada.
- (+) Conciliación automática: gold = silver en toneladas y reproduce las tasas verificadas a EE. UU.
- (−) La convención del día 15 aproxima meses con cambios a mitad de mes (abr-2025 en EE. UU.).
