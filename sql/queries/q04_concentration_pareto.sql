-- Pregunta: ¿Qué tan concentradas están las compras de vísceras de China? ¿Cuántos proveedores hacen el 80%?
-- Técnica: participación acumulada con SUM() OVER (ORDER BY ... ROWS UNBOUNDED PRECEDING) + índice HHI
-- Fuente: pork_gold.fact_china_imports, base directa (todos los orígenes), 2024 = último año completo reportado por China
-- Lectura: 5 proveedores hacen el 77,9% de las vísceras y 6 superan el 80%. HHI ≈ 1.531: concentración
--          moderada (umbral 1.500–2.500). Chile, el benchmark de Ecuador, es 8.º con 3,4%.
WITH offal AS (
  SELECT c.name_es AS supplier, SUM(f.tonnes) AS tonnes
  FROM pork_gold.fact_china_imports f
  JOIN pork_gold.dim_product p ON p.product_key = f.product_key AND p.product_group_es = 'Vísceras'
  JOIN pork_gold.dim_country c ON c.country_key = f.partner_key
  WHERE f.basis = 'direct' AND f.date_key BETWEEN 20240101 AND 20241201
  GROUP BY c.name_es
),
shares AS (
  SELECT supplier, tonnes, 100 * tonnes / SUM(tonnes) OVER () AS share FROM offal
)
SELECT ROW_NUMBER() OVER (ORDER BY tonnes DESC) AS puesto,
       supplier                                  AS proveedor,
       ROUND(tonnes)                             AS toneladas,
       ROUND(share, 1)                           AS part_pct,
       ROUND(SUM(share) OVER (ORDER BY tonnes DESC ROWS UNBOUNDED PRECEDING), 1) AS acumulado_pct,
       ROUND(SUM(share * share) OVER (), 0)      AS hhi
FROM shares
ORDER BY tonnes DESC;
