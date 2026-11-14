-- =====================================================================
-- seed/01_reference_data.sql · Datos de referencia de silver
-- Solo hechos verificados en la Fase 0 (docs/assumptions.md) o catálogos
-- oficiales. Idempotente: INSERT IGNORE + claves únicas.
-- =====================================================================

-- ---------- Fuentes ----------
INSERT IGNORE INTO pork_silver.source (name, publisher, url) VALUES
 ('comtrade',            'UN Statistics Division',                       'https://comtradeplus.un.org'),
 ('comtrade_mirror',     'UN Statistics Division (datos espejo: exportadores → China)', 'https://comtradeplus.un.org'),
 ('gacc',                'General Administration of Customs of China',   'http://stats.customs.gov.cn'),
 ('usda_psd',            'USDA Foreign Agricultural Service',            'https://apps.fas.usda.gov/psdonline'),
 ('faostat',             'FAO',                                          'https://www.fao.org/faostat'),
 ('mofcom',              'Ministry of Commerce of China',                'https://english.mofcom.gov.cn'),
 ('cn_tariff_commission','Customs Tariff Commission of the State Council (China)', 'https://gss.mof.gov.cn'),
 ('nppc',                'National Pork Producers Council (EE. UU.)',    'https://nppc.org'),
 ('usmef',               'U.S. Meat Export Federation',                  'https://www.usmef.org'),
 ('ahdb',                'AHDB (Reino Unido)',                           'https://ahdb.org.uk'),
 ('wto_tdf',             'WTO Tariff Download Facility',                 'https://tariffdata.wto.org'),
 ('woah',                'Organización Mundial de Sanidad Animal',       'https://www.woah.org'),
 ('agrocalidad',         'Agrocalidad (Ecuador)',                        'https://www.agrocalidad.gob.ec'),
 ('mag_ecuador',         'Ministerio de Agricultura, Ganadería y Pesca (Ecuador)', 'https://www.agricultura.gob.ec'),
 ('aspe',                'Asociación de Porcicultores del Ecuador',      'https://aspe.org.ec'),
 ('aprobal',             'Asociación de Productores de Alimentos Balanceados (Ecuador)', NULL),
 ('mpceip',              'Ministerio de Producción (Ecuador)',           'https://www.produccion.gob.ec'),
 ('supuesto_propio',     'Supuesto documentado del proyecto',            NULL);

-- ---------- Países (código de UN Comtrade; W00 = Mundo, agregado) ----------
INSERT IGNORE INTO pork_silver.country (iso3, comtrade_code, name_en, name_es) VALUES
 ('W00',   0,'World','Mundo'),
 ('CHN', 156,'China','China'),
 ('HKG', 344,'Hong Kong SAR','Hong Kong'),
 ('ECU', 218,'Ecuador','Ecuador'),
 ('USA', 842,'United States','Estados Unidos'),
 ('CAN', 124,'Canada','Canadá'),
 ('MEX', 484,'Mexico','México'),
 ('BRA',  76,'Brazil','Brasil'),
 ('ARG',  32,'Argentina','Argentina'),
 ('CHL', 152,'Chile','Chile'),
 ('COL', 170,'Colombia','Colombia'),
 ('BOL',  68,'Bolivia','Bolivia'),
 ('GBR', 826,'United Kingdom','Reino Unido'),
 ('RUS', 643,'Russian Federation','Rusia'),
 ('VNM', 704,'Viet Nam','Vietnam'),
 ('PHL', 608,'Philippines','Filipinas'),
 ('KOR', 410,'Republic of Korea','Corea del Sur'),
 ('JPN', 392,'Japan','Japón'),
 ('AUS',  36,'Australia','Australia'),
 ('NZL', 554,'New Zealand','Nueva Zelanda'),
 ('CHE', 757,'Switzerland','Suiza'),
 ('CRI', 188,'Costa Rica','Costa Rica'),
 -- UE27
 ('AUT',  40,'Austria','Austria'),
 ('BEL',  56,'Belgium','Bélgica'),
 ('BGR', 100,'Bulgaria','Bulgaria'),
 ('HRV', 191,'Croatia','Croacia'),
 ('CYP', 196,'Cyprus','Chipre'),
 ('CZE', 203,'Czechia','Chequia'),
 ('DNK', 208,'Denmark','Dinamarca'),
 ('EST', 233,'Estonia','Estonia'),
 ('FIN', 246,'Finland','Finlandia'),
 ('FRA', 251,'France','Francia'),
 ('DEU', 276,'Germany','Alemania'),
 ('GRC', 300,'Greece','Grecia'),
 ('HUN', 348,'Hungary','Hungría'),
 ('IRL', 372,'Ireland','Irlanda'),
 ('ITA', 380,'Italy','Italia'),
 ('LVA', 428,'Latvia','Letonia'),
 ('LTU', 440,'Lithuania','Lituania'),
 ('LUX', 442,'Luxembourg','Luxemburgo'),
 ('MLT', 470,'Malta','Malta'),
 ('NLD', 528,'Netherlands','Países Bajos'),
 ('POL', 616,'Poland','Polonia'),
 ('PRT', 620,'Portugal','Portugal'),
 ('ROU', 642,'Romania','Rumania'),
 ('SVK', 703,'Slovakia','Eslovaquia'),
 ('SVN', 705,'Slovenia','Eslovenia'),
 ('ESP', 724,'Spain','España'),
 ('SWE', 752,'Sweden','Suecia');

-- ---------- Bloque UE con fechas de adhesión (y salida del Reino Unido) ----------
INSERT IGNORE INTO pork_silver.country_group (code, name_es) VALUES ('EU', 'Unión Europea');

INSERT IGNORE INTO pork_silver.country_group_member (group_id, country_id, valid_from, valid_to)
SELECT g.group_id, c.country_id, x.valid_from, x.valid_to
FROM (
  SELECT 'BEL' iso3, DATE '1958-01-01' valid_from, DATE '9999-12-31' valid_to UNION ALL
  SELECT 'DEU','1958-01-01','9999-12-31' UNION ALL SELECT 'FRA','1958-01-01','9999-12-31' UNION ALL
  SELECT 'ITA','1958-01-01','9999-12-31' UNION ALL SELECT 'LUX','1958-01-01','9999-12-31' UNION ALL
  SELECT 'NLD','1958-01-01','9999-12-31' UNION ALL
  SELECT 'DNK','1973-01-01','9999-12-31' UNION ALL SELECT 'IRL','1973-01-01','9999-12-31' UNION ALL
  SELECT 'GBR','1973-01-01','2020-01-31' UNION ALL
  SELECT 'GRC','1981-01-01','9999-12-31' UNION ALL
  SELECT 'ESP','1986-01-01','9999-12-31' UNION ALL SELECT 'PRT','1986-01-01','9999-12-31' UNION ALL
  SELECT 'AUT','1995-01-01','9999-12-31' UNION ALL SELECT 'FIN','1995-01-01','9999-12-31' UNION ALL
  SELECT 'SWE','1995-01-01','9999-12-31' UNION ALL
  SELECT 'CYP','2004-05-01','9999-12-31' UNION ALL SELECT 'CZE','2004-05-01','9999-12-31' UNION ALL
  SELECT 'EST','2004-05-01','9999-12-31' UNION ALL SELECT 'HUN','2004-05-01','9999-12-31' UNION ALL
  SELECT 'LVA','2004-05-01','9999-12-31' UNION ALL SELECT 'LTU','2004-05-01','9999-12-31' UNION ALL
  SELECT 'MLT','2004-05-01','9999-12-31' UNION ALL SELECT 'POL','2004-05-01','9999-12-31' UNION ALL
  SELECT 'SVK','2004-05-01','9999-12-31' UNION ALL SELECT 'SVN','2004-05-01','9999-12-31' UNION ALL
  SELECT 'BGR','2007-01-01','9999-12-31' UNION ALL SELECT 'ROU','2007-01-01','9999-12-31' UNION ALL
  SELECT 'HRV','2013-07-01','9999-12-31'
) x
JOIN pork_silver.country c ON c.iso3 = x.iso3
JOIN pork_silver.country_group g ON g.code = 'EU';

-- ---------- Líneas HS del alcance ----------
-- is_ecuador_supply (SAM): solo CONGELADOS. El tránsito reefer Guayaquil–Shanghái
-- (~30+ días) hace inviable lo fresco/refrigerado (supuesto a validar en entrevistas).
INSERT IGNORE INTO pork_silver.hs_product
 (hs_code, hs4, product_group, preservation, description_es, is_ecuador_supply) VALUES
 ('020311','0203','meat','fresh_chilled','Canales y medias canales de porcino, frescas o refrigeradas', FALSE),
 ('020312','0203','meat','fresh_chilled','Piernas, paletas y sus trozos, sin deshuesar, frescos o refrigerados', FALSE),
 ('020319','0203','meat','fresh_chilled','Las demás carnes de porcino, frescas o refrigeradas', FALSE),
 ('020321','0203','meat','frozen','Canales y medias canales de porcino, congeladas', FALSE),
 ('020322','0203','meat','frozen','Piernas, paletas y sus trozos, sin deshuesar, congelados', TRUE),
 ('020329','0203','meat','frozen','Las demás carnes de porcino, congeladas', TRUE),
 ('020630','0206','offal','fresh_chilled','Despojos comestibles de porcino, frescos o refrigerados', FALSE),
 ('020641','0206','offal','frozen','Hígados de porcino, congelados', TRUE),
 ('020649','0206','offal','frozen','Los demás despojos comestibles de porcino, congelados (patas, orejas, estómagos...)', TRUE),
 ('021011','0210','processed','salted_smoked','Jamones, paletas y sus trozos, sin deshuesar, salados o ahumados', FALSE),
 ('021012','0210','processed','salted_smoked','Panceta y sus trozos, salados o ahumados', FALSE),
 ('021019','0210','processed','salted_smoked','Las demás carnes de porcino, saladas o ahumadas', FALSE);

-- ---------- Medidas comerciales de China (SCD tipo 2) ----------
-- Todas aplican a 0203 y 0206 (carne y "variety meats"). Fechas de vigencia verificadas.
-- Reconstrucción del arancel total al cerdo de EE. UU.:
--   inicio 2025: 12 NMF + 25 (232)             = 37%
--   10-mar-2025: +10 fentanilo                 = 47%
--   10-abr-2025: +84 recíproco                 = 131%
--   12-abr-2025: recíproco sube a 125          = 172%  (pico reportado por NPPC/USMEF)
--   14-may-2025: recíproco baja a 10           = 57%
--   10-nov-2025: se suspende el 10 de fentanilo = 47%  (vigente; tregua hasta 10-ene-2027)

-- NMF (aplica a todos los orígenes sin preferencia)
INSERT IGNORE INTO pork_silver.trade_measure
 (imposing_id, target_id, target_group_id, target_company, hs_code, measure_type, rate_pct, valid_from, valid_to, source_id, notes)
SELECT cn.country_id, NULL, NULL, NULL, p.hs_code, 'mfn', 12.00, '2018-01-01', '9999-12-31', s.source_id,
       'NMF 12% reportado por USMEF; VERIFICAR por línea HS en WTO TDF (Fase 4)'
FROM pork_silver.hs_product p
JOIN pork_silver.country cn ON cn.iso3 = 'CHN'
JOIN pork_silver.source  s  ON s.name  = 'usmef'
WHERE p.hs4 IN ('0203','0206');

-- Represalias contra EE. UU.
INSERT IGNORE INTO pork_silver.trade_measure
 (imposing_id, target_id, target_group_id, target_company, hs_code, measure_type, rate_pct, valid_from, valid_to, source_id, notes)
SELECT cn.country_id, us.country_id, NULL, NULL, p.hs_code, x.mtype, x.rate, x.vfrom, x.vto, s.source_id, x.notes
FROM (
  SELECT 'retaliatory_232' mtype, 25.00 rate, DATE '2018-04-02' vfrom, DATE '9999-12-31' vto, 'nppc' src,
         'Represalia por aranceles 232 (acero/aluminio) de EE. UU.' notes UNION ALL
  SELECT 'retaliatory_fentanyl', 10.00, '2025-03-10', '2025-11-09', 'usmef',
         'Suspendida desde el 10-nov-2025 (tregua de Busan)' UNION ALL
  SELECT 'reciprocal', 84.00, '2025-04-10', '2025-04-11', 'cn_tariff_commission',
         'Escalada de abril de 2025' UNION ALL
  SELECT 'reciprocal', 125.00, '2025-04-12', '2025-05-13', 'cn_tariff_commission',
         'Pico: total 172%' UNION ALL
  SELECT 'reciprocal', 10.00, '2025-05-14', '9999-12-31', 'cn_tariff_commission',
         '24% adicional suspendido; tregua prorrogada hasta el 10-ene-2027 (anuncio del 9-nov-2026)'
) x
JOIN pork_silver.hs_product p ON p.hs4 IN ('0203','0206')
JOIN pork_silver.country cn ON cn.iso3 = 'CHN'
JOIN pork_silver.country us ON us.iso3 = 'USA'
JOIN pork_silver.source  s  ON s.name  = x.src;

-- Antidumping contra la UE (rango de empresas muestreadas; detalle por empresa en la Fase 4)
INSERT IGNORE INTO pork_silver.trade_measure
 (imposing_id, target_id, target_group_id, target_company, hs_code, measure_type, rate_pct, valid_from, valid_to, source_id, notes)
SELECT cn.country_id, NULL, g.group_id, x.company, p.hs_code, x.mtype, x.rate, x.vfrom, x.vto, s.source_id, x.notes
FROM (
  SELECT 'antidumping_provisional' mtype, '(muestreadas · mínimo)' company, 15.60 rate,
         DATE '2025-09-10' vfrom, DATE '2025-12-16' vto, 'ahdb' src, 'Depósitos convertidos en derechos definitivos' notes UNION ALL
  SELECT 'antidumping_provisional', '(muestreadas · máximo)', 32.70, '2025-09-10', '2025-12-16', 'ahdb', NULL UNION ALL
  SELECT 'antidumping', '(muestreadas · mínimo)', 4.90,  '2025-12-17', '2030-12-16', 'mofcom', 'Definitivo por 5 años' UNION ALL
  SELECT 'antidumping', '(muestreadas · máximo)', 19.80, '2025-12-17', '2030-12-16', 'mofcom', 'Definitivo por 5 años'
) x
JOIN pork_silver.hs_product p ON p.hs4 IN ('0203','0206')
JOIN pork_silver.country cn ON cn.iso3 = 'CHN'
JOIN pork_silver.country_group g ON g.code = 'EU'
JOIN pork_silver.source s ON s.name = x.src;

-- ---------- Supuestos iniciales (versión 1) ----------
INSERT IGNORE INTO pork_silver.assumption
 (name, version, value_min, value_base, value_max, unit, source_id, rationale)
SELECT x.name, 1, x.vmin, x.vbase, x.vmax, x.unit, s.source_id, x.why
FROM (
  SELECT 'discount_rate' name, 10 vmin, 12 vbase, 15 vmax, '%' unit, 'supuesto_propio' src,
         'Riesgo país de Ecuador + prima sectorial; justificar con fuente en la Fase 10' why UNION ALL
  SELECT 'horizon_years', 10, 10, 10, 'años', 'supuesto_propio',
         'Una certificación sanitaria tarda de 4 a 6 años' UNION ALL
  SELECT 'certification_year', 2, 4, 6, 'años', 'supuesto_propio',
         'Escenarios de compartimentación' UNION ALL
  SELECT 'ecuador_pork_production', 230000, 240000, 240000, 't/año', 'aprobal',
         'ASPE reporta ~230 mil t; Aprobal 240 mil t (2025)' UNION ALL
  SELECT 'china_import_vat', 9, 9, 9, '%', 'supuesto_propio',
         'Se excluye de la comparación (igual para todos); verificar'
) x
JOIN pork_silver.source s ON s.name = x.src;

-- ---------- Escenarios: 3 casos comerciales × 2 autosuficiencia × 4 certificación = 24 ----------
INSERT IGNORE INTO pork_silver.scenario (code, trade_case, china_selfsuff, cert_year, description_es)
SELECT CONCAT(t.tc, '-', a.ss, '-', IFNULL(c.cy, 'NA')),
       t.tc, a.ss, c.cy,
       CONCAT(t.lbl, ' · autosuficiencia china ', IF(a.ss='up','al alza','a la baja'),
              ' · ', IF(c.cy IS NULL, 'compartimentación no lograda', CONCAT('certificación en el año ', c.cy)))
FROM (SELECT 'A' tc, 'A: la ventana se cierra' lbl UNION ALL
      SELECT 'B', 'B: statu quo' UNION ALL
      SELECT 'C', 'C: la ventana se abre') t
CROSS JOIN (SELECT 'up' ss UNION ALL SELECT 'down') a
CROSS JOIN (SELECT 2 cy UNION ALL SELECT 4 UNION ALL SELECT 6 UNION ALL SELECT NULL) c;

-- ---------- Provincias de Ecuador (código INEC) ----------
INSERT IGNORE INTO pork_silver.province (inec_code, name) VALUES
 ('01','Azuay'),('02','Bolívar'),('03','Cañar'),('04','Carchi'),('05','Cotopaxi'),
 ('06','Chimborazo'),('07','El Oro'),('08','Esmeraldas'),('09','Guayas'),('10','Imbabura'),
 ('11','Loja'),('12','Los Ríos'),('13','Manabí'),('14','Morona Santiago'),('15','Napo'),
 ('16','Pastaza'),('17','Pichincha'),('18','Tungurahua'),('19','Zamora Chinchipe'),('20','Galápagos'),
 ('21','Sucumbíos'),('22','Orellana'),('23','Santo Domingo de los Tsáchilas'),('24','Santa Elena');
