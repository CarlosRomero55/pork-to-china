-- =====================================================================
-- 001 · Medida de China contra el cerdo de Canadá
-- 25% adicional ("anti-discriminación") a la carne y las vísceras de cerdo canadienses
-- desde el 20-03-2025, en respuesta a los aranceles de Canadá a vehículos eléctricos y acero.
-- El acuerdo Canadá–China de enero de 2026 NO incluyó al cerdo: sigue vigente.
-- Fuentes: Comisión Arancelaria del Consejo de Estado (8-mar-2025); EY (31-mar-2025);
--          Farms.com y Western Producer (ene-2026).
-- =====================================================================
ALTER TABLE pork_silver.trade_measure
  MODIFY measure_type ENUM('mfn','preferential','retaliatory_232','retaliatory_fentanyl',
                           'reciprocal','retaliatory_301','antidumping_provisional','antidumping',
                           'anti_discrimination') NOT NULL;

INSERT IGNORE INTO pork_silver.source (name, publisher, url) VALUES
 ('ey_tax_alert', 'EY Global Tax Alert', 'https://www.ey.com/en_gl/technical/tax-alerts/canada-china-trade-relations-march-2025-key-developments');

INSERT IGNORE INTO pork_silver.trade_measure
 (imposing_id, target_id, target_group_id, target_company, hs_code, measure_type, rate_pct, valid_from, valid_to, source_id, notes)
SELECT cn.country_id, ca.country_id, NULL, NULL, p.hs_code, 'anti_discrimination', 25.00,
       '2025-03-20', '9999-12-31', s.source_id,
       'Represalia por aranceles de Canadá a VE y acero; no incluida en el acuerdo de ene-2026'
FROM pork_silver.hs_product p
JOIN pork_silver.country cn ON cn.iso3 = 'CHN'
JOIN pork_silver.country ca ON ca.iso3 = 'CAN'
JOIN pork_silver.source  s  ON s.name  = 'ey_tax_alert'
WHERE p.hs4 IN ('0203','0206');
