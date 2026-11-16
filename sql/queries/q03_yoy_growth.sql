-- Pregunta: ¿Cuánto crecieron o cayeron las ventas de cada proveedor a China cada año?
-- Técnica: CTE + LAG() OVER (PARTITION BY proveedor ORDER BY año) para la variación interanual
-- Fuente: pork_gold.fact_china_imports, SOLO base espejo (lo que declaran los 12 exportadores): es la única
--         base continua 2018–2026. Mezclar directo y espejo entre periodos sesga la comparación (ADR-008).
-- Lectura: 2025 castiga a Brasil (−33,8%), Canadá (−28,6%) y EE. UU. (−26,8%); el Reino Unido crece (+13,0%).
--          Casi todos caen desde 2022: China compra menos en general (ver consulta 06).
WITH yearly AS (
  SELECT c.name_es AS supplier, d.year, SUM(v.tonnes) AS tonnes
  FROM pork_gold.fact_china_imports v
  JOIN pork_gold.dim_date d    ON d.date_key = v.date_key
  JOIN pork_gold.dim_country c ON c.country_key = v.partner_key
  WHERE v.basis = 'mirror' AND d.year BETWEEN 2021 AND 2025
  GROUP BY c.name_es, d.year
),
growth AS (
  SELECT supplier, year, tonnes,
         LAG(tonnes) OVER (PARTITION BY supplier ORDER BY year) AS prev
  FROM yearly
)
SELECT supplier AS proveedor,
       ROUND(MAX(CASE WHEN year = 2025 THEN tonnes END))                    AS t_2025,
       ROUND(MAX(CASE WHEN year = 2022 THEN 100 * (tonnes - prev) / prev END), 1) AS yoy_2022,
       ROUND(MAX(CASE WHEN year = 2023 THEN 100 * (tonnes - prev) / prev END), 1) AS yoy_2023,
       ROUND(MAX(CASE WHEN year = 2024 THEN 100 * (tonnes - prev) / prev END), 1) AS yoy_2024,
       ROUND(MAX(CASE WHEN year = 2025 THEN 100 * (tonnes - prev) / prev END), 1) AS yoy_2025
FROM growth
GROUP BY supplier
ORDER BY t_2025 DESC;
