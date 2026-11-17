-- =====================================================================
-- 016 · Cerdos por provincia (INEC ESPAC) y estado sanitario (Fase 13.2)
-- ESPAC es una encuesta por muestreo de fincas: sirve para COMPARAR provincias, no para el volumen
-- nacional (ESPAC 2024: 1,72 millones de cerdos al año; ASPE: 5,5 millones beneficiados en 2021).
-- El estado sanitario se guarda a nivel nacional: los brotes por provincia no son públicos.
-- =====================================================================
INSERT IGNORE INTO pork_silver.source (name, publisher, url) VALUES
 ('inec_espac', 'INEC · Encuesta de Superficie y Producción Agropecuaria Continua (ESPAC), tabulados T57–T59',
  'https://www.ecuadorencifras.gob.ec/encuesta-de-superficie-y-produccion-agropecuaria-continua-2024/'),
 ('agrocalidad_ppc_2026', 'Agrocalidad / MAGP · campaña de vacunación contra la peste porcina clásica 2025–2026 (vía kchcomunicacion)',
  'https://kchcomunicacion.com/?p=497438'),
 ('magp_aftosa_2026', 'MAGP · Ecuador suspende la vacunación contra la fiebre aftosa (vía 333, 11-mar-2026)',
  'https://www.3tres3.com/en/print/22288'),
 ('agrocalidad_ppa_2025', 'Agrocalidad vía Teleamazonas · controles por peste porcina africana (28-nov-2025)',
  'https://www.teleamazonas.com/actualidad/noticias/ecuador/ecuador-intensifica-controles-aeropuertos-casos-peste-porcina-espana-107236/'),
 ('aspe_primicias', 'ASPE vía Primicias · provincias con mayor producción de carne de cerdo',
  'https://primicias.ec/noticias/economia/consumo-carne-cerdo-ecuador-inversion');

CREATE TABLE IF NOT EXISTS pork_silver.province_pigs (
  dpa_code        CHAR(2)      NOT NULL COMMENT 'código DPA del INEC (01 = Azuay … 24 = Santa Elena)',
  survey_year     SMALLINT UNSIGNED NOT NULL,
  province_name   VARCHAR(60)  NOT NULL,
  region          VARCHAR(20)  NOT NULL COMMENT 'Sierra, Costa, Amazonía',
  stock_head      INT UNSIGNED NOT NULL COMMENT 'existencia el día de la entrevista (T57)',
  sales_q3_head   INT UNSIGNED NOT NULL COMMENT 'ventas del 1-jul al 30-sep (T57)',
  breed_head      INT UNSIGNED NOT NULL COMMENT 'cerdos de raza (T58): indicador de tecnificación',
  pigs_per_year   INT UNSIGNED NOT NULL COMMENT 'cerdos al año, 1-ene a 31-dic (T59)',
  source_id       SMALLINT UNSIGNED NOT NULL,
  batch_id        BIGINT UNSIGNED NOT NULL,
  PRIMARY KEY (dpa_code, survey_year),
  CONSTRAINT fk_pp_source FOREIGN KEY (source_id) REFERENCES pork_silver.source (source_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS pork_silver.sanitary_status (
  disease     VARCHAR(60)  NOT NULL,
  scope       VARCHAR(40)  NOT NULL COMMENT 'nacional (no hay datos públicos por provincia)',
  status_es   VARCHAR(300) NOT NULL,
  china_risk  ENUM('bloquea', 'en camino', 'favorable') NOT NULL COMMENT 'efecto sobre el acceso a China',
  as_of       DATE         NOT NULL,
  source_id   SMALLINT UNSIGNED NOT NULL,
  PRIMARY KEY (disease, scope, as_of),
  CONSTRAINT fk_ss_source FOREIGN KEY (source_id) REFERENCES pork_silver.source (source_id)
) ENGINE=InnoDB;

INSERT IGNORE INTO pork_silver.sanitary_status (disease, scope, status_es, china_risk, as_of, source_id)
SELECT x.d, 'nacional', x.s, x.r, x.a, s.source_id
FROM (
  SELECT 'Peste porcina clásica (PPC)' d,
         'Presente; vacunación obligatoria en las 23 provincias. Campaña nov-2025 a oct-2026: 1.346.020 cerdos vacunados a mediados de julio de 2026 (meta 2.060.450). Sin zonas reconocidas como libres por la OMSA.' s,
         'bloquea' r, DATE('2026-07-15') a, 'agrocalidad_ppc_2026' src
  UNION ALL SELECT 'Fiebre aftosa',
         'Vacunación suspendida en 2026; Ecuador busca el estatus de libre sin vacunación ante la OMSA en 2027.',
         'en camino', DATE('2026-03-11'), 'magp_aftosa_2026'
  UNION ALL SELECT 'Peste porcina africana (PPA)',
         'Ausente. Controles reforzados en aeropuertos y fronteras desde nov-2025 por los casos en España.',
         'favorable', DATE('2025-11-28'), 'agrocalidad_ppa_2025'
) x JOIN pork_silver.source s ON s.name = x.src;

-- Vistas del tablero (pork_bi solo lee gold)
CREATE OR REPLACE SQL SECURITY DEFINER VIEW pork_gold.v_dash_province_pigs AS
SELECT p.dpa_code, p.survey_year, p.province_name, p.region, p.stock_head, p.sales_q3_head,
       p.breed_head, p.pigs_per_year,
       ROUND(100 * p.breed_head / NULLIF(p.stock_head, 0), 1) AS breed_pct,
       ROUND(100 * p.pigs_per_year / SUM(p.pigs_per_year) OVER (PARTITION BY p.survey_year), 2) AS share_year_pct
FROM pork_silver.province_pigs p;

CREATE OR REPLACE SQL SECURITY DEFINER VIEW pork_gold.v_dash_sanitary AS
SELECT ss.disease, ss.scope, ss.status_es, ss.china_risk, ss.as_of, s.publisher AS source, s.url
FROM pork_silver.sanitary_status ss JOIN pork_silver.source s ON s.source_id = ss.source_id;
