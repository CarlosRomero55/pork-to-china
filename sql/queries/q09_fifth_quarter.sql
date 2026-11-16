-- Pregunta: ¿Cuántas toneladas de vísceras vende cada país a China por cada tonelada de carne?
--           (el "quinto cuarto": vísceras que en el mercado local valen poco y en China valen más)
-- Técnica: pivoteo con SUM(CASE ...) + razón + RANK()
-- Fuente: pork_gold.fact_china_imports, base espejo, 2025
-- Lectura: Dinamarca y EE. UU. venden 2,3 t de vísceras por cada t de carne; Chile solo 0,6 y Brasil 0,16.
--          Los proveedores lejanos de Europa/EE. UU. monetizan en China el quinto cuarto que su mercado local no paga.
WITH mix AS (
  SELECT c.name_es AS supplier,
         SUM(CASE WHEN p.product_group_es = 'Vísceras' THEN f.tonnes ELSE 0 END) AS offal_t,
         SUM(CASE WHEN p.product_group_es = 'Carne'    THEN f.tonnes ELSE 0 END) AS meat_t,
         SUM(CASE WHEN p.product_group_es = 'Vísceras' THEN f.value_usd ELSE 0 END) AS offal_usd
  FROM pork_gold.fact_china_imports f
  JOIN pork_gold.dim_product p ON p.product_key = f.product_key
  JOIN pork_gold.dim_country c ON c.country_key = f.partner_key
  WHERE f.basis = 'mirror' AND f.date_key BETWEEN 20250101 AND 20251201
  GROUP BY c.name_es
)
SELECT supplier                                              AS proveedor,
       ROUND(offal_t)                                        AS t_visceras,
       ROUND(meat_t)                                         AS t_carne,
       ROUND(offal_t / NULLIF(meat_t, 0), 2)                 AS visceras_por_t_carne,
       ROUND(100 * offal_t / NULLIF(offal_t + meat_t, 0), 1) AS pct_visceras,
       ROUND(offal_usd / 1e6, 1)                             AS musd_visceras,
       RANK() OVER (ORDER BY offal_t / NULLIF(offal_t + meat_t, 0) DESC) AS puesto
FROM mix
WHERE offal_t + meat_t >= 1000
ORDER BY puesto;
