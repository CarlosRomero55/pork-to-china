-- Pregunta: ¿De qué tamaño es el mercado que Ecuador podría atacar (SAM: carne y vísceras congeladas) y
--           qué parte está en manos de proveedores castigados con aranceles altos (EE. UU. y Canadá)?
-- Técnica: CTE encadenadas + agregación condicional + participación de la parte "disputable"
-- Fuente: pork_gold.fact_china_imports, base espejo (12 exportadores, FOB), líneas is_sam, solo meses completos
--         (2026: ene–ago y sin Francia, que no reporta desde enero)
-- Lectura: el SAM de 2025 es 1,85 millones de t y 3.672 MUSD FOB (−14% vs 2024). El 26,8% (495 mil t) lo
--          venden EE. UU. y Canadá con aranceles de 37–47%. Captar 1% del SAM (~18.500 t) equivale a ~8% de la
--          producción de Ecuador (223.650 t en 2024).
WITH sam AS (
  SELECT d.year, d.month, c.iso3, f.tonnes, f.value_usd
  FROM pork_gold.fact_china_imports f
  JOIN pork_gold.dim_date d    ON d.date_key = f.date_key
  JOIN pork_gold.dim_product p ON p.product_key = f.product_key AND p.is_sam
  JOIN pork_gold.dim_country c ON c.country_key = f.partner_key
  JOIN pork_gold.mirror_coverage cov ON cov.date_key = f.date_key AND cov.is_complete
  WHERE f.basis = 'mirror'
),
yearly AS (
  SELECT year,
         COUNT(DISTINCT month) AS months,
         SUM(tonnes) AS tonnes,
         SUM(value_usd) AS usd,
         SUM(CASE WHEN iso3 IN ('USA', 'CAN') THEN tonnes ELSE 0 END) AS taxed_t
  FROM sam GROUP BY year
)
SELECT year                                             AS año,
       ROUND(tonnes)                                    AS sam_t,
       ROUND(usd / 1e6)                                 AS sam_musd,
       ROUND(usd / (1000 * tonnes), 2)                  AS fob_usd_kg,
       ROUND(100 * taxed_t / tonnes, 1)                 AS pct_eeuu_canada,
       ROUND(taxed_t)                                   AS t_eeuu_canada,
       months                                           AS meses
FROM yearly
ORDER BY year;
