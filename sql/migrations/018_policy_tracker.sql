-- =====================================================================
-- 018 · Rastreador de políticas (Fase 14.1)
-- Dos orígenes en una sola vista:
--   1) silver.policy_event: eventos cargados a mano con fuente (acuerdos, sanitarios, protocolos, mercado)
--   2) silver.trade_measure: cada cambio de arancel se vuelve un evento automáticamente, así el
--      rastreador se actualiza solo cuando se carga una medida nueva
-- its_role marca los cortes de la serie de tiempo interrumpida (Fase 14.2): corte_2018, corte_2020, control.
-- date_precision dice si la fecha es exacta (día) o aproximada (mes o año): no se inventan días.
-- =====================================================================
INSERT IGNORE INTO pork_silver.source (name, publisher, url) VALUES
 ('nhf_301_2018', 'National Hog Farmer · Retaliatory tariffs (11-jul-2018): China sube el arancel al cerdo de EE. UU. al 62%',
  'https://www.nationalhogfarmer.com/business/retaliatory-tariffs-underscore-importance-customer-education'),
 ('usda_exclusions', 'USDA FAS vía 333 · Chinese tariffs on U.S. pork products (exclusiones de la sección 301 desde mar-2020)',
  'https://www.3tres3.com/en/latest_swine_news/chinese-tariffs-on-u-s-pork-products_20745/'),
 ('asf_china_2018', 'The Pig Site · China confirma su primer caso de peste porcina africana (3-ago-2018)',
  'https://www.thepigsite.com/news/2018/08/china-culls-1000-pigs-as-first-case-of-african-swine-fever-confirmed-1'),
 ('ustr_phase_one', 'USTR · Phase One Agreement, hoja resumen de agricultura (firmado el 15-ene-2020)',
  'https://ustr.gov/sites/default/files/files/agreements/phase%20one%20agreement/Phase_One_Agreement-Ag_Summary_Short_Fact_Sheet.pdf'),
 ('phase_one_force', 'Hogan Lovells · Phase One entra en vigor el 14-feb-2020',
  'https://www.hoganlovells.com/en/publications/trade-truce-united-states-and-china-reach-phase-one-agreement'),
 ('vistazo_tlc_ecu', 'Vistazo · El TLC Ecuador–China entra en vigencia el 1-may-2024',
  'https://www.vistazo.com/politica/nacional/acuerdo-comercial-entre-china-y-ecuador-entra-en-vigencia-hay-productos-de-exportacion-con-0-de-arancel-AY7256398'),
 ('bolivia_ppc_2026', '333 · La OMSA reconoce a Santa Cruz (Bolivia) como zona libre de PPC (may-2026)',
  'https://www.3tres3.com/ultima-hora/la-omsa-reconoce-una-nueva-zona-libre-de-ppc-en-bolivia_53438/');

CREATE TABLE IF NOT EXISTS pork_silver.policy_event (
  event_id         INT UNSIGNED NOT NULL AUTO_INCREMENT,
  event_date       DATE         NOT NULL,
  date_precision   ENUM('dia', 'mes', 'año') NOT NULL DEFAULT 'dia',
  country_iso3     CHAR(3)      NOT NULL COMMENT 'país al que afecta o que actúa',
  category         ENUM('arancel', 'acuerdo', 'sanitario', 'protocolo', 'mercado') NOT NULL,
  title_es         VARCHAR(160) NOT NULL,
  detail_es        VARCHAR(400) NOT NULL,
  effect_es        VARCHAR(200) NOT NULL COMMENT 'efecto esperado sobre el cerdo hacia China',
  its_role         ENUM('corte_2018', 'corte_2020', 'control') NULL,
  source_id        SMALLINT UNSIGNED NOT NULL,
  PRIMARY KEY (event_id),
  UNIQUE KEY uq_event (event_date, country_iso3, title_es),
  CONSTRAINT fk_pe_source FOREIGN KEY (source_id) REFERENCES pork_silver.source (source_id)
) ENGINE=InnoDB;

INSERT IGNORE INTO pork_silver.policy_event
  (event_date, date_precision, country_iso3, category, title_es, detail_es, effect_es, its_role, source_id)
SELECT x.d, x.p, x.c, x.cat, x.t, x.det, x.eff, x.its, s.source_id
FROM (
  SELECT DATE('2006-01-01') d, 'año' p, 'CHL' c, 'acuerdo' cat, 'Entra en vigor el TLC Chile–China' t,
         'Primer TLC de China con un país latinoamericano; el cerdo chileno queda con arancel cero.' det,
         'Chile compite con ventaja arancelaria' eff, NULL its, 'chilecarne' src
  UNION ALL SELECT DATE('2011-01-01'), 'año', 'CRI', 'acuerdo', 'Entra en vigor el TLC Costa Rica–China',
         'El cerdo costarricense queda en libre comercio.', 'Costa Rica compite con ventaja arancelaria', NULL, 'ey_costa_rica'
  UNION ALL SELECT DATE('2011-04-01'), 'mes', 'BRA', 'protocolo', 'China aprueba las 3 primeras plantas de cerdo de Brasil',
         'Siete años después del protocolo de 2004; solo plantas de zonas libres.', 'Brasil entra al mercado chino', NULL, 'br_china_2011'
  UNION ALL SELECT DATE('2011-05-11'), 'dia', 'CHL', 'mercado', 'Primer envío de cerdo chileno a China',
         'Tras la autorización de plantas en abril de 2011.', 'Chile entra al mercado chino', NULL, 'chile_china_2011'
  UNION ALL SELECT DATE('2015-05-01'), 'mes', 'CHL', 'sanitario', 'La OMSA reconoce a Chile libre de peste porcina clásica',
         'La enfermedad se había erradicado en 1998.', 'Refuerza el acceso sanitario de Chile', NULL, 'chile_sag_ppc'
  UNION ALL SELECT DATE('2018-01-01'), 'año', 'CRI', 'sanitario', 'La OMSA reconoce a Costa Rica libre de peste porcina clásica',
         'Autodeclarada libre desde 2009.', 'Habilita el protocolo con China', NULL, 'cr_oie_2020'
  UNION ALL SELECT DATE('2018-07-06'), 'dia', 'USA', 'arancel', 'China suma 25% por la sección 301: el cerdo de EE. UU. paga 62%',
         'Segunda represalia de 2018, sobre el 12% NMF y el 25% de la 232. Desde mar-2020 los importadores pueden pedir exclusión de la 301 (no de la 232). OJO: el modelo de costo puesto en destino no la incluye (usa 37% en 2018).',
         'EE. UU. pierde competitividad frente a Europa y Brasil', 'corte_2018', 'nhf_301_2018'
  UNION ALL SELECT DATE('2018-08-03'), 'dia', 'CHN', 'sanitario', 'Primer caso de peste porcina africana en China',
         'Shenyang (Liaoning). La PPA redujo la piara china y disparó las importaciones de 2019–2020.',
         'Sube la demanda china de importación (efecto que hay que separar de los aranceles)', 'control', 'asf_china_2018'
  UNION ALL SELECT DATE('2018-10-01'), 'mes', 'ECU', 'sanitario', 'Ecuador designa Galápagos como zona libre de PPC',
         'Zona reconocida por la OMSA; el territorio continental, donde está la producción, sigue con PPC.',
         'Sin efecto para exportar desde el continente', NULL, 'woah_csf_2024'
  UNION ALL SELECT DATE('2019-11-04'), 'dia', 'BRA', 'protocolo', 'China habilita 7 plantas de Santa Catarina para vísceras de cerdo',
         'Solo del estado libre de aftosa sin vacunación.', 'Brasil compite en vísceras', NULL, 'br_offal_2019'
  UNION ALL SELECT DATE('2019-12-01'), 'mes', 'CRI', 'protocolo', 'China abre su mercado al cerdo de Costa Rica',
         'Después de un proceso iniciado en 2013.', 'Costa Rica entra al mercado chino', NULL, 'cr_china_2020'
  UNION ALL SELECT DATE('2020-01-15'), 'dia', 'USA', 'acuerdo', 'EE. UU. y China firman el acuerdo Fase Uno',
         'Compromiso chino de comprar al menos 40.000 MUSD al año en productos agrícolas y ampliación de los productos de cerdo admitidos.',
         'EE. UU. recupera parte del mercado', 'corte_2020', 'ustr_phase_one'
  UNION ALL SELECT DATE('2020-02-14'), 'dia', 'USA', 'acuerdo', 'Entra en vigor el acuerdo Fase Uno',
         'Los aranceles de represalia siguen, pero se abren exclusiones.', 'EE. UU. recupera parte del mercado', 'corte_2020', 'phase_one_force'
  UNION ALL SELECT DATE('2020-02-14'), 'dia', 'CRI', 'mercado', 'Sale el primer contenedor de cerdo de Costa Rica a China',
         'Incluye patas, trompas y orejas.', 'Nuevo competidor en vísceras', NULL, 'cr_china_2020'
  UNION ALL SELECT DATE('2020-03-01'), 'mes', 'USA', 'arancel', 'China abre exclusiones de la sección 301 para el cerdo de EE. UU.',
         'Cada importador puede pedir no pagar el 25% de la 301; el 25% de la 232 se mantiene.',
         'El arancel efectivo de EE. UU. baja para importadores con exclusión', 'corte_2020', 'usda_exclusions'
  UNION ALL SELECT DATE('2024-05-01'), 'dia', 'ECU', 'acuerdo', 'Entra en vigor el TLC Ecuador–China',
         'El cerdo ecuatoriano entra en desgravación gradual (supuesto: 15 años lineales); falta el protocolo sanitario.',
         'Mejora el precio puesto en destino de Ecuador, sin acceso sanitario todavía', NULL, 'vistazo_tlc_ecu'
  UNION ALL SELECT DATE('2024-12-01'), 'mes', 'CHL', 'protocolo', 'Chile amplía su protocolo: carne refrigerada y subproductos',
         'Antes solo podía exportar carne congelada.', 'Chile compite también en vísceras', NULL, 'chile_subproducts_2024'
  UNION ALL SELECT DATE('2025-11-28'), 'dia', 'ECU', 'sanitario', 'Ecuador refuerza controles contra la peste porcina africana',
         'Por los casos en España; Ecuador sigue libre de PPA.', 'Protege el estatus sanitario', NULL, 'agrocalidad_ppa_2025'
  UNION ALL SELECT DATE('2026-03-11'), 'dia', 'ECU', 'sanitario', 'Ecuador suspende la vacunación contra la fiebre aftosa',
         'Busca el estatus de libre sin vacunación ante la OMSA en 2027.', 'Paso previo al acceso sanitario', NULL, 'magp_aftosa_2026'
  UNION ALL SELECT DATE('2026-05-22'), 'dia', 'BOL', 'sanitario', 'La OMSA reconoce a Santa Cruz (Bolivia) libre de PPC',
         'Un vecino andino logra una zona libre en su principal región productora.', 'Muestra la ruta por zonas para Ecuador', NULL, 'bolivia_ppc_2026'
) x JOIN pork_silver.source s ON s.name = x.src;

-- Vista del rastreador: eventos manuales + cambios de arancel derivados de trade_measure
CREATE OR REPLACE SQL SECURITY DEFINER VIEW pork_gold.v_dash_policy_events AS
SELECT pe.event_date, pe.date_precision, pe.country_iso3, COALESCE(c.name_es, pe.country_iso3) AS country_es,
       pe.category, pe.title_es, pe.detail_es, pe.effect_es, pe.its_role, 'manual' AS origin,
       s.publisher AS source, s.url
FROM pork_silver.policy_event pe
JOIN pork_silver.source s ON s.source_id = pe.source_id
LEFT JOIN pork_silver.country c ON c.iso3 = pe.country_iso3
UNION ALL
SELECT m.valid_from, 'dia',
       COALESCE(ct.iso3, CASE WHEN m.target_group_id IS NOT NULL THEN 'EU' ELSE 'WLD' END),
       COALESCE(ct.name_es, CASE WHEN m.target_group_id IS NOT NULL THEN 'Unión Europea' ELSE 'Todos los proveedores' END),
       'arancel',
       CONCAT('China: ', CASE m.measure_type
                WHEN 'mfn' THEN 'arancel NMF'
                WHEN 'retaliatory_232' THEN 'represalia por la sección 232'
                WHEN 'retaliatory_fentanyl' THEN 'represalia por el arancel del fentanilo'
                WHEN 'anti_discrimination' THEN 'arancel antidiscriminación'
                WHEN 'reciprocal' THEN 'arancel recíproco'
                WHEN 'antidumping_provisional' THEN 'antidumping provisional'
                WHEN 'antidumping' THEN 'antidumping definitivo'
                ELSE m.measure_type END, ' de ',
              REPLACE(CASE WHEN MIN(m.rate_pct) = MAX(m.rate_pct) THEN TRIM(TRAILING '.' FROM TRIM(TRAILING '0' FROM CAST(MIN(m.rate_pct) AS CHAR)))
                   ELSE CONCAT(TRIM(TRAILING '.' FROM TRIM(TRAILING '0' FROM CAST(MIN(m.rate_pct) AS CHAR))), '–',
                               TRIM(TRAILING '.' FROM TRIM(TRAILING '0' FROM CAST(MAX(m.rate_pct) AS CHAR)))) END, '.', ','), '%'),
       COALESCE(MAX(m.notes), ''), 'Cambia el arancel aplicado',
       CASE WHEN m.measure_type = 'retaliatory_232' AND m.valid_from = '2018-04-02' THEN 'corte_2018' END,
       'trade_measure', MAX(s.publisher), MAX(s.url)
FROM pork_silver.trade_measure m
JOIN pork_silver.source s ON s.source_id = m.source_id
LEFT JOIN pork_silver.country ct ON ct.country_id = m.target_id
WHERE m.imposing_id = (SELECT country_id FROM pork_silver.country WHERE iso3 = 'CHN')
  AND m.valid_from > '2018-01-01'                       -- 2018-01-01 es el inicio de la serie, no un evento
  AND m.measure_type <> 'preferential'                  -- los TLC se registran a mano; la desgravación anual no es noticia
GROUP BY m.valid_from, m.measure_type, ct.iso3, ct.name_es, m.target_group_id;
