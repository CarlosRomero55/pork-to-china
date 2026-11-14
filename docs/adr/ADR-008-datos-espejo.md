# ADR-008 · Datos espejo (mirror) para cubrir el rezago de China en Comtrade

- **Estado:** Aceptada
- **Fecha:** 2026-11-13

## Contexto
La extracción real mostró que China publicó en Comtrade sus importaciones mensuales solo hasta 2024-12 (confirmado con la API de disponibilidad `getDa`). El periodo de las medidas que estudiamos (2025–2026) quedaba vacío.

## Decisión
Además de los datos directos (lo que reporta China), se extraen los **datos espejo**: lo que los 12 principales exportadores declaran haberle vendido a China (flujo X, socio 156). En silver se guardan como fuente separada (`comtrade_mirror`); nunca se mezclan con la fuente `comtrade`.

## Conciliación (2018–2024, años con ambos lados)
- Peso: China / exportadores = **0,992** (ponderado). Los tonelajes espejo son confiables (±1%).
- Valor: China (CIF) / exportadores (FOB) = **1,037** (ponderado), coherente con flete y seguro.
- Excepciones: EE. UU. 0,947 (China reporta menos de lo que EE. UU. declara exportar: posible tránsito por Hong Kong o desfase de fechas); Brasil 1,148 (flete largo).

## Consecuencias
- (+) El análisis de 2025–2026 es posible y se basa en datos oficiales.
- (+) La conciliación cuantifica el sesgo en lugar de ignorarlo.
- (−) Para 2025–2026 los valores se expresan en FOB; para comparar con años anteriores se usan tonelajes o el factor 1,037.
- (−) Los exportadores fuera de los 12 seleccionados no aparecen en el espejo; su peso se estima con el directo 2024.
