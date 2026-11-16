-- Pregunta: ¿En qué meses compra más China? Índice estacional para planificar embarques (vísceras y carne).
-- Técnica: CTE + participación de cada mes en su año con SUM() OVER (PARTITION BY año), promediada entre años;
--          índice = 100 × participación media × 12 (100 = mes promedio)
-- Fuente: pork_gold.fact_china_imports, base espejo, 2022–2025 (años completos, después del pico de la PPA)
-- Lectura: estacionalidad moderada (±8%). Vísceras: picos en noviembre (108), marzo (106) y octubre (105);
--          piso en septiembre (93). Conviene que los embarques lleguen en octubre–noviembre.
WITH monthly AS (
  SELECT p.product_group_es AS product_group, d.year, d.month, d.month_name_es, SUM(f.tonnes) AS tonnes
  FROM pork_gold.fact_china_imports f
  JOIN pork_gold.dim_date d    ON d.date_key = f.date_key
  JOIN pork_gold.dim_product p ON p.product_key = f.product_key
  WHERE f.basis = 'mirror' AND d.year BETWEEN 2022 AND 2025 AND p.product_group_es IN ('Carne', 'Vísceras')
  GROUP BY p.product_group_es, d.year, d.month, d.month_name_es
),
shares AS (
  SELECT *, tonnes / SUM(tonnes) OVER (PARTITION BY product_group, year) AS share FROM monthly
)
SELECT month                                                             AS mes,
       month_name_es                                                     AS nombre,
       ROUND(1200 * AVG(CASE WHEN product_group = 'Vísceras' THEN share END), 0) AS indice_visceras,
       ROUND(1200 * AVG(CASE WHEN product_group = 'Carne'    THEN share END), 0) AS indice_carne,
       ROUND(AVG(CASE WHEN product_group = 'Vísceras' THEN tonnes END))  AS t_visceras_prom
FROM shares
GROUP BY month, month_name_es
ORDER BY month;
