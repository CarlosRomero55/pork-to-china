-- =====================================================================
-- 02_silver.sql · Capa SILVER · 3FN, única versión de la verdad
-- Unidades crudas (kg, USD). Las conversiones (t, USD/kg, %) van en gold.
-- Idempotente: se puede ejecutar varias veces sin error.
-- =====================================================================

CREATE DATABASE IF NOT EXISTS pork_silver
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

-- ---------- Catálogos ----------
CREATE TABLE IF NOT EXISTS pork_silver.country (
  country_id     SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
  iso3           CHAR(3)      NOT NULL,
  comtrade_code  SMALLINT UNSIGNED NOT NULL COMMENT 'código de país en UN Comtrade (Francia = 251, no 250)',
  name_en        VARCHAR(80)  NOT NULL,
  name_es        VARCHAR(80)  NOT NULL,
  PRIMARY KEY (country_id),
  UNIQUE KEY uq_country_iso3 (iso3),
  UNIQUE KEY uq_country_comtrade (comtrade_code)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS pork_silver.country_group (
  group_id  SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
  code      VARCHAR(20) NOT NULL,
  name_es   VARCHAR(80) NOT NULL,
  PRIMARY KEY (group_id),
  UNIQUE KEY uq_group_code (code)
) ENGINE=InnoDB;

-- Pertenencia con vigencia: el Reino Unido fue UE hasta el 31-01-2020
CREATE TABLE IF NOT EXISTS pork_silver.country_group_member (
  group_id    SMALLINT UNSIGNED NOT NULL,
  country_id  SMALLINT UNSIGNED NOT NULL,
  valid_from  DATE NOT NULL,
  valid_to    DATE NOT NULL DEFAULT '9999-12-31',
  PRIMARY KEY (group_id, country_id, valid_from),
  CONSTRAINT ck_member_dates CHECK (valid_to >= valid_from),
  CONSTRAINT fk_member_group   FOREIGN KEY (group_id)   REFERENCES pork_silver.country_group (group_id),
  CONSTRAINT fk_member_country FOREIGN KEY (country_id) REFERENCES pork_silver.country (country_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS pork_silver.hs_product (
  hs_code            CHAR(6)  NOT NULL,
  hs4                CHAR(4)  NOT NULL,
  product_group      ENUM('meat','offal','processed') NOT NULL,
  preservation       ENUM('fresh_chilled','frozen','salted_smoked') NOT NULL,
  description_es     VARCHAR(200) NOT NULL,
  is_ecuador_supply  BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'TRUE = línea que Ecuador podría ofrecer (define el SAM)',
  PRIMARY KEY (hs_code),
  CONSTRAINT ck_hs_prefix CHECK (LEFT(hs_code, 4) = hs4)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS pork_silver.source (
  source_id  SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
  name       VARCHAR(60)  NOT NULL,
  publisher  VARCHAR(120) NOT NULL,
  url        VARCHAR(500) NULL,
  PRIMARY KEY (source_id),
  UNIQUE KEY uq_source_name (name)
) ENGINE=InnoDB;

-- ---------- Comercio ----------
CREATE TABLE IF NOT EXISTS pork_silver.trade_flow (
  flow_id        BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  reporter_id    SMALLINT UNSIGNED NOT NULL,
  partner_id     SMALLINT UNSIGNED NOT NULL,
  hs_code        CHAR(6) NOT NULL,
  period         DATE    NOT NULL COMMENT 'primer día del mes',
  flow_type      ENUM('M','X') NOT NULL COMMENT 'M = importación, X = exportación',
  net_weight_kg  DECIMAL(18,2) NULL,
  value_usd      DECIMAL(18,2) NOT NULL,
  source_id      SMALLINT UNSIGNED NOT NULL,
  batch_id       BIGINT UNSIGNED NOT NULL COMMENT 'trazabilidad hacia pork_bronze.extract_batch',
  loaded_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (flow_id),
  UNIQUE KEY uq_flow (reporter_id, partner_id, hs_code, period, flow_type, source_id),
  KEY ix_flow_period_hs (period, hs_code),
  KEY ix_flow_partner_period (partner_id, period),
  CONSTRAINT ck_flow_day1   CHECK (DAY(period) = 1),
  CONSTRAINT ck_flow_values CHECK (value_usd >= 0 AND (net_weight_kg IS NULL OR net_weight_kg >= 0)),
  CONSTRAINT fk_flow_reporter FOREIGN KEY (reporter_id) REFERENCES pork_silver.country (country_id),
  CONSTRAINT fk_flow_partner  FOREIGN KEY (partner_id)  REFERENCES pork_silver.country (country_id),
  CONSTRAINT fk_flow_hs       FOREIGN KEY (hs_code)     REFERENCES pork_silver.hs_product (hs_code),
  CONSTRAINT fk_flow_source   FOREIGN KEY (source_id)   REFERENCES pork_silver.source (source_id)
) ENGINE=InnoDB;

-- ---------- Medidas comerciales · SCD tipo 2 (ADR-002) ----------
-- Destino: un país (target_id), un bloque (target_group_id) o todos (ambos NULL = NMF).
CREATE TABLE IF NOT EXISTS pork_silver.trade_measure (
  measure_id       INT UNSIGNED NOT NULL AUTO_INCREMENT,
  imposing_id      SMALLINT UNSIGNED NOT NULL,
  target_id        SMALLINT UNSIGNED NULL,
  target_group_id  SMALLINT UNSIGNED NULL,
  target_company   VARCHAR(120) NULL COMMENT 'antidumping: tasa por empresa',
  hs_code          CHAR(6) NOT NULL,
  measure_type     ENUM('mfn','preferential','retaliatory_232','retaliatory_fentanyl',
                        'reciprocal','retaliatory_301','antidumping_provisional','antidumping') NOT NULL,
  rate_pct         DECIMAL(6,2) NOT NULL,
  valid_from       DATE NOT NULL,
  valid_to         DATE NOT NULL DEFAULT '9999-12-31' COMMENT '9999-12-31 = sin fecha de fin conocida',
  source_id        SMALLINT UNSIGNED NOT NULL,
  notes            VARCHAR(500) NULL,
  -- Columna técnica: permite una clave única aunque haya NULLs
  target_key       VARCHAR(160) AS (CONCAT(IFNULL(target_id,0),'|',IFNULL(target_group_id,0),'|',IFNULL(target_company,''))) STORED,
  PRIMARY KEY (measure_id),
  UNIQUE KEY uq_measure_version (imposing_id, target_key, hs_code, measure_type, valid_from),
  KEY ix_measure_lookup (hs_code, target_id, valid_from, valid_to),
  CONSTRAINT ck_measure_dates  CHECK (valid_to >= valid_from),
  CONSTRAINT ck_measure_rate   CHECK (rate_pct >= 0 AND rate_pct <= 1000),
  CONSTRAINT ck_measure_target CHECK (NOT (target_id IS NOT NULL AND target_group_id IS NOT NULL)),
  CONSTRAINT fk_measure_imposing FOREIGN KEY (imposing_id)     REFERENCES pork_silver.country (country_id),
  CONSTRAINT fk_measure_target   FOREIGN KEY (target_id)       REFERENCES pork_silver.country (country_id),
  CONSTRAINT fk_measure_group    FOREIGN KEY (target_group_id) REFERENCES pork_silver.country_group (group_id),
  CONSTRAINT fk_measure_hs       FOREIGN KEY (hs_code)         REFERENCES pork_silver.hs_product (hs_code),
  CONSTRAINT fk_measure_source   FOREIGN KEY (source_id)       REFERENCES pork_silver.source (source_id)
) ENGINE=InnoDB;

-- Vista: medidas vigentes HOY. "Vigente" se calcula con la fecha, no con una
-- columna fija, porque el antidumping a la UE ya tiene fecha de fin programada (2030-12-16).
CREATE OR REPLACE VIEW pork_silver.v_trade_measure_current AS
SELECT m.*
FROM pork_silver.trade_measure m
WHERE CURDATE() BETWEEN m.valid_from AND m.valid_to;

-- ---------- Supuestos versionados (ADR-003) y escenarios ----------
CREATE TABLE IF NOT EXISTS pork_silver.assumption (
  assumption_id  INT UNSIGNED NOT NULL AUTO_INCREMENT,
  name           VARCHAR(60) NOT NULL,
  version        SMALLINT UNSIGNED NOT NULL DEFAULT 1,
  value_min      DECIMAL(18,4) NOT NULL,
  value_base     DECIMAL(18,4) NOT NULL,
  value_max      DECIMAL(18,4) NOT NULL,
  unit           VARCHAR(30) NOT NULL,
  source_id      SMALLINT UNSIGNED NULL,
  rationale      TEXT NULL,
  created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (assumption_id),
  UNIQUE KEY uq_assumption_version (name, version),
  CONSTRAINT ck_assumption_range CHECK (value_min <= value_base AND value_base <= value_max),
  CONSTRAINT fk_assumption_source FOREIGN KEY (source_id) REFERENCES pork_silver.source (source_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS pork_silver.scenario (
  scenario_id     TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
  code            VARCHAR(20) NOT NULL,
  trade_case      ENUM('A','B','C') NOT NULL COMMENT 'A = ventana se cierra, B = statu quo, C = ventana se abre',
  china_selfsuff  ENUM('up','down') NOT NULL,
  cert_year       TINYINT UNSIGNED NULL COMMENT '2, 4, 6 o NULL = compartimentación no lograda',
  description_es  VARCHAR(255) NOT NULL,
  PRIMARY KEY (scenario_id),
  UNIQUE KEY uq_scenario_code (code),
  CONSTRAINT ck_scenario_cert CHECK (cert_year IS NULL OR cert_year IN (2,4,6))
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS pork_silver.scenario_assumption (
  scenario_id    TINYINT UNSIGNED NOT NULL,
  assumption_id  INT UNSIGNED NOT NULL,
  which_value    ENUM('min','base','max') NOT NULL DEFAULT 'base',
  PRIMARY KEY (scenario_id, assumption_id),
  CONSTRAINT fk_sa_scenario   FOREIGN KEY (scenario_id)   REFERENCES pork_silver.scenario (scenario_id),
  CONSTRAINT fk_sa_assumption FOREIGN KEY (assumption_id) REFERENCES pork_silver.assumption (assumption_id)
) ENGINE=InnoDB;

-- ---------- Sanidad ----------
CREATE TABLE IF NOT EXISTS pork_silver.province (
  province_id  TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
  inec_code    CHAR(2) NOT NULL,
  name         VARCHAR(60) NOT NULL,
  PRIMARY KEY (province_id),
  UNIQUE KEY uq_province_inec (inec_code)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS pork_silver.canton (
  canton_id    SMALLINT UNSIGNED NOT NULL AUTO_INCREMENT,
  province_id  TINYINT UNSIGNED NOT NULL,
  inec_code    CHAR(4) NOT NULL,
  name         VARCHAR(80) NOT NULL,
  PRIMARY KEY (canton_id),
  UNIQUE KEY uq_canton_inec (inec_code),
  CONSTRAINT fk_canton_province FOREIGN KEY (province_id) REFERENCES pork_silver.province (province_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS pork_silver.sanitary_case (
  case_id    INT UNSIGNED NOT NULL AUTO_INCREMENT,
  canton_id  SMALLINT UNSIGNED NOT NULL,
  disease    ENUM('PPC','PPA','FA') NOT NULL,
  period     DATE NOT NULL,
  outbreaks  INT UNSIGNED NOT NULL DEFAULT 0,
  cases      INT UNSIGNED NOT NULL DEFAULT 0,
  source_id  SMALLINT UNSIGNED NOT NULL,
  batch_id   BIGINT UNSIGNED NOT NULL,
  PRIMARY KEY (case_id),
  UNIQUE KEY uq_case (canton_id, disease, period),
  CONSTRAINT ck_case_day1 CHECK (DAY(period) = 1),
  CONSTRAINT fk_case_canton FOREIGN KEY (canton_id) REFERENCES pork_silver.canton (canton_id),
  CONSTRAINT fk_case_source FOREIGN KEY (source_id) REFERENCES pork_silver.source (source_id)
) ENGINE=InnoDB;
