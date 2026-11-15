-- =====================================================================
-- 003 · Balance de cerdo de USDA PSD en silver
-- Formato largo (una fila por país × año comercial × atributo): agregar un atributo
-- nuevo de USDA no exige cambiar el esquema. Gold lo pivotea.
-- =====================================================================
CREATE TABLE IF NOT EXISTS pork_silver.psd_country (
  psd_code         VARCHAR(4)  NOT NULL COMMENT 'código propio de USDA FAS (CH = China, AS = Australia)',
  name             VARCHAR(80) NOT NULL,
  country_id       SMALLINT UNSIGNED NULL COMMENT 'NULL = no está en el catálogo (se conserva igual)',
  country_group_id SMALLINT UNSIGNED NULL COMMENT 'para agregados como la Unión Europea (E4)',
  PRIMARY KEY (psd_code),
  CONSTRAINT fk_psdc_country FOREIGN KEY (country_id)       REFERENCES pork_silver.country (country_id),
  CONSTRAINT fk_psdc_group   FOREIGN KEY (country_group_id) REFERENCES pork_silver.country_group (group_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS pork_silver.psd_balance (
  psd_code      VARCHAR(4)  NOT NULL,
  market_year   SMALLINT UNSIGNED NOT NULL,
  attribute     VARCHAR(60) NOT NULL COMMENT 'Production, Imports, Domestic Consumption...',
  value         DECIMAL(16,3) NULL,
  unit          VARCHAR(30) NOT NULL COMMENT '(1000 MT CWE) o (PERCENT)',
  released      CHAR(7)     NULL COMMENT 'AAAA-MM de la publicación de USDA para ese país',
  source_id     SMALLINT UNSIGNED NOT NULL,
  batch_id      BIGINT UNSIGNED NOT NULL,
  PRIMARY KEY (psd_code, market_year, attribute),
  KEY ix_psd_year_attr (market_year, attribute),
  CONSTRAINT fk_psdb_country FOREIGN KEY (psd_code)  REFERENCES pork_silver.psd_country (psd_code),
  CONSTRAINT fk_psdb_source  FOREIGN KEY (source_id) REFERENCES pork_silver.source (source_id)
) ENGINE=InnoDB;
