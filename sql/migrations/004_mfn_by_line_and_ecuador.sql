-- =====================================================================
-- 004 · Arancel NMF de China por línea HS, acuerdo Ecuador–China y producción de Ecuador
--
-- Fuentes (consultadas el 15-nov-2026):
--   NMF 2026 por línea: arancel de importación de China (Comisión Arancelaria del Consejo de
--     Estado), consultado vía htshub.com y treayo.com (tablas GACC 2026).
--   Tasa provisional de 8% en 2020-2021: plan de ajuste arancelario 2020 de la Comisión
--     Arancelaria (3tres3, 18-dic-2019) y retorno al 12% el 1-ene-2022 (3tres3, 17-dic-2021;
--     USDA GAIN CH2021-0169).
--   Acuerdo Ecuador–China: vigente desde 1-may-2024; "proteínas crudas de res y cerdo: 15 años"
--     (El Comercio, 10-may-2023). Calendario por línea NO verificado → supuesto.
--   Producción de Ecuador: ASPE (vía 333 Latinoamérica) y MAG (sep-2024).
-- =====================================================================

INSERT IGNORE INTO pork_silver.source (name, publisher, url) VALUES
 ('cn_tariff_2026', 'Arancel de importación de China 2026 (vía htshub / treayo, tablas GACC)', 'https://www.htshub.com/cn-hs/'),
 ('el_comercio',    'Diario El Comercio (Ecuador)', 'https://www.elcomercio.com/actualidad/negocios/historico-acuerdo-comercial-ecuador-china/');

-- ---------------------------------------------------------------------
-- 1. Corrección: las líneas frescas/refrigeradas pagan 20%, no 12%.
--    Es un dato mal sembrado (no un cambio en el tiempo) → se corrige en sitio.
-- ---------------------------------------------------------------------
UPDATE pork_silver.trade_measure m
JOIN pork_silver.country cn ON cn.country_id = m.imposing_id AND cn.iso3 = 'CHN'
JOIN pork_silver.source  s  ON s.name = 'cn_tariff_2026'
SET m.rate_pct = 20.00, m.source_id = s.source_id,
    m.notes = 'NMF verificado por línea (2026): fresco o refrigerado 20%. Corrige el 12% sembrado'
WHERE m.measure_type = 'mfn' AND m.target_id IS NULL
  AND m.hs_code IN ('020311','020312','020319','020630');

UPDATE pork_silver.trade_measure m
JOIN pork_silver.country cn ON cn.country_id = m.imposing_id AND cn.iso3 = 'CHN'
JOIN pork_silver.source  s  ON s.name = 'cn_tariff_2026'
SET m.source_id = s.source_id, m.notes = 'NMF verificado por línea (2026): congelado 12%'
WHERE m.measure_type = 'mfn' AND m.target_id IS NULL
  AND m.hs_code IN ('020321','020322','020329','020641','020649');

-- ---------------------------------------------------------------------
-- 2. Procesados (0210): no tenían medida → NMF 25%
-- ---------------------------------------------------------------------
INSERT IGNORE INTO pork_silver.trade_measure
 (imposing_id, target_id, target_group_id, target_company, hs_code, measure_type, rate_pct, valid_from, valid_to, source_id, notes)
SELECT cn.country_id, NULL, NULL, NULL, p.hs_code, 'mfn', 25.00, '2018-01-01', '9999-12-31', s.source_id,
       'NMF verificado por línea (2026): salado, seco o ahumado 25%'
FROM pork_silver.hs_product p
JOIN pork_silver.country cn ON cn.iso3 = 'CHN'
JOIN pork_silver.source  s  ON s.name  = 'cn_tariff_2026'
WHERE p.hs4 = '0210';

-- ---------------------------------------------------------------------
-- 3. SCD tipo 2 real: 020322 y 020329 tuvieron tasa provisional de 8% en 2020-2021.
--    Se cierra la versión original y se abren dos nuevas (8% y regreso a 12%).
-- ---------------------------------------------------------------------
UPDATE pork_silver.trade_measure m
JOIN pork_silver.country cn ON cn.country_id = m.imposing_id AND cn.iso3 = 'CHN'
SET m.valid_to = '2019-12-31'
WHERE m.measure_type = 'mfn' AND m.target_id IS NULL AND m.valid_from = '2018-01-01'
  AND m.hs_code IN ('020322','020329');

INSERT IGNORE INTO pork_silver.trade_measure
 (imposing_id, target_id, target_group_id, target_company, hs_code, measure_type, rate_pct, valid_from, valid_to, source_id, notes)
SELECT cn.country_id, NULL, NULL, NULL, p.hs_code, 'mfn', x.rate, x.vfrom, x.vto, s.source_id, x.notes
FROM (
  SELECT 8.00 rate, DATE '2020-01-01' vfrom, DATE '2021-12-31' vto,
         'Tasa provisional 8% (plan arancelario 2020-2021, escasez por PPA)' notes UNION ALL
  SELECT 12.00, DATE '2022-01-01', DATE '9999-12-31',
         'Regreso al NMF 12% desde 1-ene-2022 (USDA GAIN CH2021-0169)'
) x
JOIN pork_silver.hs_product p ON p.hs_code IN ('020322','020329')
JOIN pork_silver.country cn ON cn.iso3 = 'CHN'
JOIN pork_silver.source  s  ON s.name  = 'cn_tariff_commission';

-- ---------------------------------------------------------------------
-- 4. Acuerdo Ecuador–China (SUPUESTO): desgravación lineal en 15 años desde el NMF
--    de cada línea de carne y vísceras crudas (0203, 0206). Primer corte al entrar en
--    vigor (1-may-2024) y luego cada 1 de enero → 0% desde 2038.
--    Reemplaza al NMF para Ecuador (no se suma); solo aplica si hay protocolo sanitario.
-- ---------------------------------------------------------------------
INSERT IGNORE INTO pork_silver.trade_measure
 (imposing_id, target_id, target_group_id, target_company, hs_code, measure_type, rate_pct, valid_from, valid_to, source_id, notes)
WITH RECURSIVE k AS (SELECT 1 AS n UNION ALL SELECT n + 1 FROM k WHERE n < 15)
SELECT cn.country_id, ec.country_id, NULL, NULL, p.hs_code, 'preferential',
       ROUND(IF(p.preservation = 'fresh_chilled', 20, 12) * (15 - k.n) / 15, 2),
       IF(k.n = 1, DATE '2024-05-01', MAKEDATE(2023 + k.n, 1)),
       IF(k.n = 15, DATE '9999-12-31', MAKEDATE(2024 + k.n, 1) - INTERVAL 1 DAY),
       s.source_id,
       CONCAT('SUPUESTO: año ', k.n, '/15 de desgravación lineal (El Comercio: "proteínas crudas de cerdo: 15 años"); ',
              'calendario oficial por línea no verificado. Reemplaza al NMF; requiere protocolo sanitario')
FROM k
JOIN pork_silver.hs_product p ON p.hs4 IN ('0203','0206')
JOIN pork_silver.country cn ON cn.iso3 = 'CHN'
JOIN pork_silver.country ec ON ec.iso3 = 'ECU'
JOIN pork_silver.source  s  ON s.name  = 'supuesto_propio';

-- ---------------------------------------------------------------------
-- 5. Producción nacional (USDA dejó de seguir a Ecuador en 2015)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pork_silver.country_production (
  country_id    SMALLINT UNSIGNED NOT NULL,
  year          SMALLINT UNSIGNED NOT NULL,
  source_id     SMALLINT UNSIGNED NOT NULL,
  production_t  DECIMAL(14,1) NOT NULL COMMENT 'toneladas de carne de cerdo',
  is_estimate   BOOLEAN NOT NULL DEFAULT FALSE,
  notes         VARCHAR(300) NULL,
  PRIMARY KEY (country_id, year, source_id),
  CONSTRAINT fk_cprod_country FOREIGN KEY (country_id) REFERENCES pork_silver.country (country_id),
  CONSTRAINT fk_cprod_source  FOREIGN KEY (source_id)  REFERENCES pork_silver.source (source_id)
) ENGINE=InnoDB;

INSERT IGNORE INTO pork_silver.country_production (country_id, year, source_id, production_t, is_estimate, notes)
SELECT ec.country_id, x.yr, s.source_id, x.t, x.est, x.notes
FROM (
  SELECT 'aspe' src, 2023 yr, 213000.0 t, FALSE est, 'ASPE vía 333 Latinoamérica' notes UNION ALL
  SELECT 'aspe', 2024, 223650.0, TRUE,  'ASPE: +5% sobre 2023 (≈2,76 millones de cerdos faenados)' UNION ALL
  SELECT 'mag_ecuador', 2023, 216389.0, FALSE, 'MAG, sep-2024 (estimación nacional)'
) x
JOIN pork_silver.source  s  ON s.name  = x.src
JOIN pork_silver.country ec ON ec.iso3 = 'ECU';
