-- Pregunta: ¿Quién ganó y quién perdió participación en China tras el arancel a EE. UU. (marzo 2025)?
--           12 meses antes (2024-03 a 2025-02) vs 12 meses después (2025-03 a 2026-02), carne y vísceras por separado.
-- Técnica: CTE + agregación condicional + participación con SUM() OVER (PARTITION BY ...)
-- Fuente: pork_gold.fact_china_imports, SOLO base espejo (lo que declaran los 12 exportadores): es la única
--         base continua 2018–2026. Mezclar directo y espejo entre periodos sesga la comparación (ADR-008).
-- Lectura: (datos a 2026-09) en carne perdieron los castigados con aranceles —Brasil −4,6 pp, Canadá −4,1 pp,
--          EE. UU. −1,3 pp— y ganó España (+4,0 pp) pese al antidumping. En vísceras, el nicho de Ecuador, el gran
--          perdedor es EE. UU. (−31%, −5,9 pp) y ganan España, Reino Unido y Dinamarca: el hueco lo llenó Europa.
WITH periods AS (
  SELECT c.name_es AS supplier, p.product_group_es AS product_group,
         SUM(CASE WHEN v.date_key BETWEEN 20240301 AND 20250201 THEN v.tonnes ELSE 0 END) AS t_before,
         SUM(CASE WHEN v.date_key BETWEEN 20250301 AND 20260201 THEN v.tonnes ELSE 0 END) AS t_after
  FROM pork_gold.fact_china_imports v
  JOIN pork_gold.dim_country c ON c.country_key = v.partner_key
  JOIN pork_gold.dim_product p ON p.product_key = v.product_key
  WHERE v.basis = 'mirror' AND p.product_group_es IN ('Carne', 'Vísceras')
  GROUP BY c.name_es, p.product_group_es
),
shares AS (
  SELECT *,
         100 * t_before / SUM(t_before) OVER (PARTITION BY product_group) AS share_before,
         100 * t_after  / SUM(t_after)  OVER (PARTITION BY product_group) AS share_after
  FROM periods
)
SELECT product_group                         AS grupo,
       supplier                              AS proveedor,
       ROUND(t_before)                       AS t_antes,
       ROUND(t_after)                        AS t_despues,
       ROUND(100 * (t_after - t_before) / NULLIF(t_before, 0), 1) AS cambio_pct,
       ROUND(share_before, 1)                AS part_antes,
       ROUND(share_after, 1)                 AS part_despues,
       ROUND(share_after - share_before, 1)  AS cambio_pp
FROM shares
ORDER BY grupo, cambio_pp DESC;
