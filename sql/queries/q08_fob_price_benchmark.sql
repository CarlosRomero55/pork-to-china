-- Pregunta: ¿A qué precio FOB vende cada proveedor a China en las líneas del SAM? ¿Dónde queda Chile,
--           la referencia de precio para Ecuador?
-- Técnica: CTE + valor unitario ponderado (SUM(valor)/SUM(kg)) + PERCENT_RANK() y diferencia contra Chile
--          con MAX(CASE ...) OVER (PARTITION BY línea)
-- Fuente: pork_gold.fact_china_imports, base espejo (FOB: lo que cobra el exportador), 2025, sin filas
--         marcadas como atípicas ni proveedores con menos de 500 t en la línea
-- Lectura: Chile es el más barato en carne congelada (020329: 1,35 USD/kg FOB) y vende vísceras (020649) a
--          1,60 USD/kg, percentil 33, por debajo de España (1,86) y EE. UU. (1,90). Referencia de ingreso para
--          Ecuador en el modelo financiero: ~1,60 USD/kg FOB en vísceras.
WITH prices AS (
  SELECT p.hs_code, p.description_es, c.name_es AS supplier,
         SUM(f.tonnes) AS tonnes, SUM(f.value_usd) / (1000 * SUM(f.tonnes)) AS fob_usd_kg
  FROM pork_gold.fact_china_imports f
  JOIN pork_gold.dim_product p ON p.product_key = f.product_key AND p.is_sam
  JOIN pork_gold.dim_country c ON c.country_key = f.partner_key
  WHERE f.basis = 'mirror' AND f.date_key BETWEEN 20250101 AND 20251201
    AND NOT f.is_outlier AND f.tonnes > 0
  GROUP BY p.hs_code, p.description_es, c.name_es
  HAVING SUM(f.tonnes) >= 500
)
SELECT hs_code                                                    AS hs,
       supplier                                                   AS proveedor,
       ROUND(tonnes)                                              AS toneladas,
       ROUND(fob_usd_kg, 2)                                       AS fob_usd_kg,
       ROUND(100 * PERCENT_RANK() OVER (PARTITION BY hs_code ORDER BY fob_usd_kg), 0) AS percentil,
       ROUND(fob_usd_kg - MAX(CASE WHEN supplier = 'Chile' THEN fob_usd_kg END)
                          OVER (PARTITION BY hs_code), 2)         AS vs_chile
FROM prices
ORDER BY hs, fob_usd_kg DESC;
