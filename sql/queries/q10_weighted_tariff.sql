-- Pregunta: ¿Cuánto arancel paga en promedio el cerdo que entra a China, ponderado por volumen, y cómo cambió?
-- Técnica: unión de dos tablas de hechos por sus claves comunes + media ponderada SUM(tasa × t) / SUM(t)
--          + LAG() para el cambio interanual en puntos
-- Fuente: pork_gold.fact_china_imports (espejo, 12 exportadores) × pork_gold.fact_tariff_applied (arancel efectivo
--         mínimo: NMF o acuerdo + adicionales + antidumping mínimo), 2018–2026, solo meses completos
-- Lectura: el arancel promedio que paga la víscera que entra a China subió de 19,1% (2024) a 26,1% (2025),
--          +7,0 pp: China sigue comprando a proveedores castigados. Un proveedor con 0–10% tendría ventaja real.
WITH weighted AS (
  SELECT d.year,
         p.product_group_es AS product_group,
         SUM(t.effective_min_pct * f.tonnes) / SUM(f.tonnes) AS avg_tariff,
         SUM(f.tonnes) AS tonnes
  FROM pork_gold.fact_china_imports f
  JOIN pork_gold.fact_tariff_applied t
       ON t.date_key = f.date_key AND t.origin_key = f.partner_key AND t.product_key = f.product_key
  JOIN pork_gold.dim_date d    ON d.date_key = f.date_key
  JOIN pork_gold.dim_product p ON p.product_key = f.product_key
  JOIN pork_gold.mirror_coverage cov ON cov.date_key = f.date_key AND cov.is_complete
  WHERE f.basis = 'mirror' AND p.product_group_es IN ('Carne', 'Vísceras')
  GROUP BY d.year, p.product_group_es
)
SELECT year                                                                          AS año,
       ROUND(MAX(CASE WHEN product_group = 'Carne' THEN avg_tariff END), 1)          AS arancel_carne,
       ROUND(MAX(CASE WHEN product_group = 'Vísceras' THEN avg_tariff END), 1)       AS arancel_visceras,
       ROUND(MAX(CASE WHEN product_group = 'Vísceras' THEN avg_tariff END)
           - LAG(MAX(CASE WHEN product_group = 'Vísceras' THEN avg_tariff END)) OVER (ORDER BY year), 1) AS cambio_visceras_pp,
       ROUND(SUM(tonnes))                                                            AS toneladas
FROM weighted
GROUP BY year
ORDER BY year;
