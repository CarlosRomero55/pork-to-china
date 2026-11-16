-- =====================================================================
-- 007 · Gold: balance de mercado (USDA PSD) y producción nacional
-- Unidades distintas → tablas distintas: USDA en miles de t CWE (sin vísceras);
-- Comtrade en toneladas de peso neto. Nunca se suman entre sí.
-- =====================================================================

-- Grano: área USDA × año comercial. Incluye áreas que no están en dim_country
-- (p. ej. la UE como bloque, E4), por eso la clave es el código de USDA.
CREATE TABLE IF NOT EXISTS pork_gold.fact_market_balance (
  psd_code               VARCHAR(4)  NOT NULL,
  market_year            SMALLINT UNSIGNED NOT NULL,
  area_name              VARCHAR(80) NOT NULL,
  country_key            SMALLINT UNSIGNED NULL COMMENT 'NULL = bloque o país fuera del catálogo',
  production_kt          DECIMAL(12,1) NULL COMMENT 'miles de t CWE',
  imports_kt             DECIMAL(12,1) NULL,
  exports_kt             DECIMAL(12,1) NULL,
  consumption_kt         DECIMAL(12,1) NULL,
  ending_stocks_kt       DECIMAL(12,1) NULL,
  import_share_pct       DECIMAL(6,2)  NULL COMMENT 'importaciones / consumo',
  self_sufficiency_pct   DECIMAL(6,2)  NULL COMMENT 'producción / consumo',
  is_projection          BOOLEAN NOT NULL COMMENT 'año aún no cerrado: estimación o proyección de USDA',
  released               CHAR(7) NULL COMMENT 'publicación de USDA (AAAA-MM)',
  PRIMARY KEY (psd_code, market_year),
  KEY ix_fmb_country (country_key),
  CONSTRAINT fk_fmb_country FOREIGN KEY (country_key) REFERENCES pork_gold.dim_country (country_key)
) ENGINE=InnoDB;

-- Grano: país × año × fuente (se conservan las fuentes que discrepan, p. ej. ASPE vs MAG)
CREATE TABLE IF NOT EXISTS pork_gold.fact_domestic_production (
  country_key   SMALLINT UNSIGNED NOT NULL,
  year          SMALLINT UNSIGNED NOT NULL,
  source_name   VARCHAR(60) NOT NULL,
  production_t  DECIMAL(14,1) NOT NULL,
  is_estimate   BOOLEAN NOT NULL,
  notes         VARCHAR(300) NULL,
  PRIMARY KEY (country_key, year, source_name),
  CONSTRAINT fk_fdp_country FOREIGN KEY (country_key) REFERENCES pork_gold.dim_country (country_key)
) ENGINE=InnoDB;
