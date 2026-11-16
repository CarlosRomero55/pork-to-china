-- Pregunta: ¿Cómo cambió el ranking de proveedores de cerdo de China año a año (2018–2025)?
-- Técnica: CTE + RANK() OVER (PARTITION BY año ORDER BY toneladas DESC) + pivoteo con MAX(CASE ...)
-- Fuente: pork_gold.fact_china_imports, SOLO base espejo (lo que declaran los 12 exportadores): es la única
--         base continua 2018–2026. Mezclar directo y espejo entre periodos sesga la comparación (ADR-008).
-- Lectura: España es el n.º 1 desde 2019. Alemania pasó del 1.º puesto (2018) al 11.º tras la PPA (2020).
--          Chile se mantiene entre el 7.º y el 10.º: un proveedor chico pero estable.
WITH yearly AS (
  SELECT d.year, c.name_es AS supplier, SUM(v.tonnes) AS tonnes
  FROM pork_gold.fact_china_imports v
  JOIN pork_gold.dim_date d    ON d.date_key = v.date_key
  JOIN pork_gold.dim_country c ON c.country_key = v.partner_key
  WHERE v.basis = 'mirror' AND d.year BETWEEN 2018 AND 2025
  GROUP BY d.year, c.name_es
),
ranked AS (
  SELECT *, RANK() OVER (PARTITION BY year ORDER BY tonnes DESC) AS rnk FROM yearly
)
SELECT supplier AS proveedor,
       MAX(CASE WHEN year = 2018 THEN rnk END) AS `2018`,
       MAX(CASE WHEN year = 2019 THEN rnk END) AS `2019`,
       MAX(CASE WHEN year = 2020 THEN rnk END) AS `2020`,
       MAX(CASE WHEN year = 2021 THEN rnk END) AS `2021`,
       MAX(CASE WHEN year = 2022 THEN rnk END) AS `2022`,
       MAX(CASE WHEN year = 2023 THEN rnk END) AS `2023`,
       MAX(CASE WHEN year = 2024 THEN rnk END) AS `2024`,
       MAX(CASE WHEN year = 2025 THEN rnk END) AS `2025`
FROM ranked
GROUP BY supplier
ORDER BY `2025`;
