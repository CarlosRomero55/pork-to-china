-- Pregunta: En cada línea del SAM, ¿quién es el proveedor n.º 1 hoy, desde cuándo, y cuántas veces cambió el líder?
-- Técnica: ROW_NUMBER() para el líder de cada mes + LAG() para detectar el cambio + conteo de "rachas"
--          (técnica gaps-and-islands)
-- Fuente: pork_gold.fact_china_imports, base espejo, solo meses completos (mirror_coverage: en 2026-09
--         solo habían reportado Brasil y Chile, y Chile aparecía como líder)
-- Lectura: el liderazgo es inestable: en vísceras (020649) cambió 34 veces desde 2018 entre solo 3 países, y
--          EE. UU. vuelve a liderar en 2026 pese al 47%. En carne congelada con hueso (020322) España lidera desde 2022.
WITH monthly AS (
  SELECT p.hs_code, f.date_key, c.name_es AS supplier, f.tonnes,
         ROW_NUMBER() OVER (PARTITION BY p.hs_code, f.date_key ORDER BY f.tonnes DESC) AS rn
  FROM pork_gold.fact_china_imports f
  JOIN pork_gold.dim_product p ON p.product_key = f.product_key AND p.is_sam
  JOIN pork_gold.dim_country c ON c.country_key = f.partner_key
  JOIN pork_gold.mirror_coverage cov ON cov.date_key = f.date_key AND cov.is_complete
  WHERE f.basis = 'mirror' AND f.tonnes > 0
),
leaders AS (
  SELECT hs_code, date_key, supplier,
         LAG(supplier) OVER (PARTITION BY hs_code ORDER BY date_key) AS prev_leader
  FROM monthly WHERE rn = 1
),
streaks AS (
  SELECT *, SUM(CASE WHEN prev_leader IS NULL OR prev_leader <> supplier THEN 1 ELSE 0 END)
              OVER (PARTITION BY hs_code ORDER BY date_key) AS streak_id
  FROM leaders
),
last_streak AS (
  SELECT hs_code, MAX(streak_id) AS streak_id FROM streaks GROUP BY hs_code
)
SELECT s.hs_code                                        AS hs,
       MAX(s.supplier)                                  AS lider_actual,
       DATE_FORMAT(MIN(DATE(s.date_key)), '%Y-%m')      AS lider_desde,
       COUNT(*)                                         AS meses_seguidos,
       (SELECT COUNT(*) - 1 FROM (SELECT DISTINCT hs_code, streak_id FROM streaks) x
         WHERE x.hs_code = s.hs_code)                   AS cambios_de_lider,
       (SELECT COUNT(DISTINCT supplier) FROM leaders l WHERE l.hs_code = s.hs_code) AS lideres_distintos
FROM streaks s
JOIN last_streak ls ON ls.hs_code = s.hs_code AND ls.streak_id = s.streak_id
GROUP BY s.hs_code
ORDER BY s.hs_code;
