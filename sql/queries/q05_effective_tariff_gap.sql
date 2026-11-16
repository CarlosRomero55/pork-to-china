-- Pregunta: Hoy, ¿cuánto arancel paga cada proveedor en las líneas que Ecuador podría vender (SAM),
--           y a cuántos puntos está del mejor? ¿Tiene acceso sanitario?
-- Técnica: CTE + MIN() OVER (PARTITION BY línea) para la brecha contra el mejor + RANK()
-- Fuente: pork_gold.fact_tariff_applied (último mes con datos de aranceles = mes actual)
-- Lectura: Chile paga 0% en las líneas del SAM; Ecuador pagaría 9,6% con el acuerdo, mejor que Brasil (12%)
--          y que la UE (16,9–31,8%), pero NO tiene acceso sanitario. La barrera de Ecuador no es el arancel.
WITH latest AS (
  SELECT MAX(d.date_key) AS date_key FROM pork_gold.dim_date d WHERE d.date <= CURDATE()
),
sam AS (
  SELECT p.hs_code, c.name_es AS supplier, c.exports_pork_to_china AS access_ok,
         t.effective_min_pct AS eff_min, t.effective_max_pct AS eff_max
  FROM pork_gold.fact_tariff_applied t
  JOIN latest l                ON l.date_key = t.date_key
  JOIN pork_gold.dim_product p ON p.product_key = t.product_key AND p.is_sam
  JOIN pork_gold.dim_country c ON c.country_key = t.origin_key
  WHERE c.iso3 IN ('USA','CAN','ESP','DNK','NLD','DEU','BRA','CHL','ECU')
)
SELECT hs_code                                          AS hs,
       supplier                                         AS proveedor,
       IF(access_ok, 'sí', 'NO')                         AS acceso,
       eff_min                                          AS efectivo_min,
       eff_max                                          AS efectivo_max,
       eff_min - MIN(eff_min) OVER (PARTITION BY hs_code) AS brecha_pp,
       RANK() OVER (PARTITION BY hs_code ORDER BY eff_min) AS puesto
FROM sam
WHERE hs_code IN ('020329', '020649')
ORDER BY hs, puesto, proveedor;
