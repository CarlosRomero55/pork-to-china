# ADR-010 · Convenciones del modelo financiero de AgroPorc

- **Estado:** Aceptada
- **Fecha:** 2026-11-16

## Contexto
El proyecto debe responder si a una empresa porcícola ecuatoriana (AgroPorc, ficticia) le conviene invertir
para exportar vísceras congeladas a China, en 24 escenarios. Varios insumos no tienen fuente pública.

## Decisiones
1. **USD reales**, sin inflación; horizonte de 10 años (año 0 = 2026); tasa de descuento 12% (rango 10–15%).
2. **Adecuación de una planta existente**, no planta nueva (decisión de Carlos): la inversión es frío,
   adecuación sanitaria y habilitación para China.
3. **La víscera se valora a su costo de oportunidad** (lo que valdría en el mercado local), no a cero:
   exportarla significa dejar de venderla en Ecuador.
4. **El dato sin fuente se convierte en resultado:** como el valor local de la víscera no está publicado,
   el modelo calcula el **máximo que tolera cada escenario (VAN = 0)**. La conclusión se expresa como
   "exportar conviene si la víscera vale menos de X USD/kg en Ecuador".
5. **Impuesto efectivo 36,25%** y **sin arrastre de pérdidas** (conservador). Capital de trabajo de 2 meses
   de costo variable, recuperado en el año 10. Depreciación lineal a 10 años.
6. **Ecuador es tomador de precio:** vende al FOB de Chile (1,60 USD/kg en vísceras, 2025).
7. Los escenarios sin certificación pierden toda la inversión: el modelo no supone que se recupere.

## Consecuencias
- (+) Cada número del resultado se puede rastrear a un supuesto versionado con su fuente o su marca de "supuesto".
- (+) La incertidumbre más grande queda visible en vez de enterrada en un valor elegido.
- (−) Los costos operativos sin fuente pueden estar subestimados; la Fase 14 (Monte Carlo) mide su efecto.
