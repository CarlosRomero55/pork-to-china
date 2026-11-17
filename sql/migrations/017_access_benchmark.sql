-- =====================================================================
-- 017 · Benchmark de acceso sanitario a China (Fase 13.3) + corrección del estado de la PPC
-- Corrección: la 016 decía que Ecuador no tiene zonas libres de PPC. La OMSA SÍ reconoce como libre
-- la zona insular de Galápagos (designada en 2018); el territorio continental, donde está toda la
-- producción, no. La 016 no se edita (ya se aplicó): se corrige aquí.
-- =====================================================================
INSERT IGNORE INTO pork_silver.source (name, publisher, url) VALUES
 ('woah_csf_2024', 'OMSA · Resolución 26 (91.ª SG, 2024): estatus de los Miembros respecto de la peste porcina clásica',
  'https://woah.org/app/uploads/2024/06/91gs-2024-res-26-tech-csf-status-final-sp.pdf'),
 ('chile_china_2011', 'The Pig Site · First shipment of Chilean pork to China (11-may-2011); ODEPA (29-abr-2011)',
  'https://thepigsite.com/news/2011/05/first-shipment-of-chilean-pork-to-china-1'),
 ('chile_sag_ppc', 'SAG · Informe de sanidad 2024 (PPC erradicada en 1998); ASPROCER vía 333 (OMSA, may-2015)',
  'https://sag.cl/sites/default/files/Informe%20Sanidad%202024%20%2816-05-2025%29%20Pliego.pdf'),
 ('chile_subproducts_2024', 'Diario Financiero · Chile y China firman protocolos (carne refrigerada y subproductos de cerdo)',
  'https://www.df.cl/empresas/consumo/chile-y-china-firman-protocolos-para-ampliar-las-exportaciones-de-frutas'),
 ('cr_china_2020', 'El Observador CR · Exportación de cerdo a China: un hito que tomó siete años (feb-2020)',
  'https://observador.cr/noticia/exportacion-de-cerdo-a-china-un-hito-que-tomo-siete-anos/'),
 ('cr_oie_2020', 'MAPA España · Boletín 447: la OIE ratifica el estatus de Costa Rica (libre de PPC desde 2018)',
  'https://www.mapa.gob.es/images/fr/_bne44721costaricaag-sanprag_tcm36-537583.pdf'),
 ('br_china_2011', 'Revista Cultivar · Brasil quer dobrar venda de carnes para China (abr-2011); protocolo de 2004',
  'https://www.revistacultivar.com.br/noticias/brasil-quer-dobrar-venda-de-carnes-para-china'),
 ('br_offal_2019', 'NSC Total · Sete frigoríficos de SC habilitados a exportar subprodutos suínos à China (nov-2019)',
  'https://www.nsctotal.com.br/?p=6624214');

-- Corrección del estado de la PPC (nueva fila con fecha de hoy; la anterior queda como historia)
INSERT IGNORE INTO pork_silver.sanitary_status (disease, scope, status_es, china_risk, as_of, source_id)
SELECT 'Peste porcina clásica (PPC)', 'nacional',
       'Presente en el territorio continental, con vacunación obligatoria en las 23 provincias (1.346.020 cerdos vacunados a jul-2026, meta 2.060.450). La OMSA solo reconoce como libre la zona insular de Galápagos.',
       'bloquea', DATE('2026-11-16'), s.source_id
FROM pork_silver.source s WHERE s.name = 'woah_csf_2024';

-- La vista sanitaria muestra solo la versión más reciente de cada enfermedad
CREATE OR REPLACE SQL SECURITY DEFINER VIEW pork_gold.v_dash_sanitary AS
SELECT ss.disease, ss.scope, ss.status_es, ss.china_risk, ss.as_of, s.publisher AS source, s.url
FROM pork_silver.sanitary_status ss
JOIN pork_silver.source s ON s.source_id = ss.source_id
WHERE ss.as_of = (SELECT MAX(x.as_of) FROM pork_silver.sanitary_status x
                  WHERE x.disease = ss.disease AND x.scope = ss.scope);

CREATE TABLE IF NOT EXISTS pork_silver.access_benchmark (
  iso3              CHAR(3)      NOT NULL,
  country_es        VARCHAR(40)  NOT NULL,
  csf_status_es     VARCHAR(200) NOT NULL COMMENT 'peste porcina clásica',
  fmd_status_es     VARCHAR(200) NOT NULL COMMENT 'fiebre aftosa',
  process_start     SMALLINT UNSIGNED NULL COMMENT 'año de inicio del proceso o del protocolo con China',
  market_open       SMALLINT UNSIGNED NULL COMMENT 'año de la primera aprobación de plantas / apertura',
  first_export      SMALLINT UNSIGNED NULL COMMENT 'año del primer envío',
  offal_access_es   VARCHAR(200) NOT NULL COMMENT 'acceso para vísceras y subproductos',
  regionalized      TINYINT(1)   NOT NULL COMMENT '1 = entró con una zona, no con todo el país',
  lesson_es         VARCHAR(300) NOT NULL,
  source_id         SMALLINT UNSIGNED NOT NULL,
  PRIMARY KEY (iso3),
  CONSTRAINT fk_ab_source FOREIGN KEY (source_id) REFERENCES pork_silver.source (source_id)
) ENGINE=InnoDB;

INSERT IGNORE INTO pork_silver.access_benchmark
  (iso3, country_es, csf_status_es, fmd_status_es, process_start, market_open, first_export, offal_access_es,
   regionalized, lesson_es, source_id)
SELECT x.iso3, x.c, x.csf, x.fmd, x.ps, x.mo, x.fe, x.offal, x.reg, x.lesson, s.source_id
FROM (
  SELECT 'CHL' iso3, 'Chile' c, 'Erradicada en 1998 (SAG); libre reconocido por la OMSA en 2015' csf,
         'Libre' fmd, NULL ps, 2011 mo, 2011 fe,
         'Protocolo ampliado a carne refrigerada y subproductos congelados (dic-2024)' offal, 0 reg,
         'Entró ya libre de PPC y con TLC (2006): el acceso fue rápido una vez abierto el mercado.' lesson, 'chile_china_2011' src
  UNION ALL SELECT 'CRI', 'Costa Rica', 'Autodeclarada libre en 2009; libre reconocido por la OMSA en 2018',
         'Libre sin vacunación', 2013, 2019, 2020,
         'Desde el primer envío: patas, trompas, orejas, piel y grasa', 0,
         'País pequeño como Ecuador: ~7 años desde el protocolo (2013) hasta el primer contenedor (feb-2020).', 'cr_china_2020'
  UNION ALL SELECT 'BRA', 'Brasil', 'Libre por zonas (estados del sur); el norte y el nordeste no',
         'Santa Catarina libre sin vacunación desde 2007', 2004, 2011, 2011,
         'Siete plantas de Santa Catarina habilitadas para subproductos (nov-2019)', 1,
         'Entró por regiones: China aprobó plantas de las zonas libres, no de todo el país. ~7 años desde el protocolo (2004).', 'br_china_2011'
  UNION ALL SELECT 'ECU', 'Ecuador', 'Presente en el continente con vacunación; solo Galápagos es zona libre (OMSA)',
         'Vacunación suspendida en 2026; busca libre sin vacunación en 2027', NULL, NULL, NULL,
         'Sin protocolo', 0,
         'Necesita primero una zona libre de PPC en el continente (como Santa Catarina en Brasil o Santa Cruz en Bolivia, 2026).', 'woah_csf_2024'
) x JOIN pork_silver.source s ON s.name = x.src;

CREATE OR REPLACE SQL SECURITY DEFINER VIEW pork_gold.v_dash_access_benchmark AS
SELECT b.iso3, b.country_es, b.csf_status_es, b.fmd_status_es, b.process_start, b.market_open, b.first_export,
       b.first_export - b.process_start AS years_to_first_export, b.offal_access_es, b.regionalized,
       b.lesson_es, s.publisher AS source, s.url
FROM pork_silver.access_benchmark b JOIN pork_silver.source s ON s.source_id = b.source_id;
