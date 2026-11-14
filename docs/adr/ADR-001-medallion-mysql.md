# ADR-001 · Arquitectura Medallion en MySQL

- **Estado:** Aceptada
- **Fecha:** 2026-11-13

## Contexto
El estudio combina fuentes heterogéneas (APIs de comercio, anuncios arancelarios, PDFs sanitarios, entrevistas) que se corrigen o cambian con el tiempo. La recomendación final podría implicar inversiones millonarias, así que cada cifra debe poder rastrearse hasta su origen y su fecha de extracción. Volumen esperado: pocos millones de filas. Entorno: Windows, MySQL 8, Python, Power BI Desktop.

## Decisión
Tres esquemas en MySQL:
- **bronze:** respuestas crudas e inmutables, con source_name, extracted_at y batch_id.
- **silver:** modelo limpio en 3FN; única versión de la verdad (enfoque Inmon).
- **gold:** esquema estrella (Kimball); lo único que consumen Power BI y la API.

La transformación se hace en Python (pandas), en lotes idempotentes e incrementales.

## Alternativas consideradas
- Base única sin capas: descartada porque se pierde la trazabilidad.
- Inmon puro o Kimball puro: se combinan (silver = Inmon, gold = Kimball).
- Lakehouse (Fabric/Databricks): excesivo para el volumen; queda como ruta de migración.
- Lambda/Kappa: los datos son mensuales; el streaming no aporta.
- ELT puro en SQL: la conciliación, los outliers y Monte Carlo son más claros en Python.

## Consecuencias
- (+) Reproducibilidad: se puede reconstruir el análisis "tal como se veía" en cualquier fecha.
- (+) El diseño migra casi 1:1 a Microsoft Fabric (Files/Delta, notebooks, Direct Lake).
- (−) Más tablas y scripts que mantener.
- (−) MySQL no escala horizontalmente; aceptable para este volumen.
