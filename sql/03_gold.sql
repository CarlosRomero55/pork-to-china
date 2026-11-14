-- =====================================================================
-- 03_gold.sql · Capa GOLD · esquema estrella (Kimball)
-- Lo único que leen Power BI y la API. Se reconstruye desde silver
-- (build_gold.py), así que las facts pueden vaciarse y recargarse.
-- Idempotente: se puede ejecutar varias veces sin error.
-- =====================================================================

CREATE DATABASE IF NOT EXISTS pork_gold
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

-- ---------- Dimensiones ----------
CREATE TABLE IF NOT EXISTS pork_gold.dim_date (
  date_key              INT UNSIGNED NOT NULL COMMENT 'AAAAMMDD, ej. 20250301',
  date                  DATE NOT NULL,
  year                  SMALLINT UNSIGNED NOT NULL,
  quarter               TINYINT UNSIGNED NOT NULL,
  month                 TINYINT UNSIGNED NOT NULL,
  month_name_es         VARCHAR(12) NOT NULL,
  year_month_label      CHAR(7) NOT NULL COMMENT 'AAAA-MM',
  months_from_us_cut    SMALLINT NOT NULL COMMENT 'meses desde 2025-03 (negativo = antes)',
  months_from_eu_cut    SMALLINT NOT NULL COMMENT 'meses desde 2025-09 (antidumping provisional)',
  PRIMARY KEY (date_key),
  UNIQUE KEY uq_dim_date (date)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS pork_gold.dim_country (
  country_key    SMALLINT UNSIGNED NOT NULL,
  iso3           CHAR(3) NOT NULL,
  name_es        VARCHAR(80) NOT NULL,
  supplier_bloc  VARCHAR(20) NOT NULL COMMENT 'UE, EE. UU., Brasil, Canadá, Reino Unido, Otros',
  PRIMARY KEY (country_key),
  UNIQUE KEY uq_dim_country_iso3 (iso3)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS pork_gold.dim_product (
  product_key       SMALLINT UNSIGNED NOT NULL,
  hs_code           CHAR(6) NOT NULL,
  product_group_es  VARCHAR(20) NOT NULL COMMENT 'Carne, Vísceras, Procesado',
  description_es    VARCHAR(200) NOT NULL,
  is_sam            BOOLEAN NOT NULL,
  PRIMARY KEY (product_key),
  UNIQUE KEY uq_dim_product_hs (hs_code)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS pork_gold.dim_scenario (
  scenario_key    TINYINT UNSIGNED NOT NULL,
  code            VARCHAR(20) NOT NULL,
  trade_case      CHAR(1) NOT NULL,
  china_selfsuff  VARCHAR(4) NOT NULL,
  cert_year       TINYINT UNSIGNED NULL,
  label_es        VARCHAR(120) NOT NULL,
  PRIMARY KEY (scenario_key),
  UNIQUE KEY uq_dim_scenario_code (code)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS pork_gold.dim_province (
  province_key  TINYINT UNSIGNED NOT NULL,
  inec_code     CHAR(2) NOT NULL,
  name          VARCHAR(60) NOT NULL,
  PRIMARY KEY (province_key)
) ENGINE=InnoDB;

-- ---------- Hechos ----------
-- Grano: socio–HS–mes (importaciones de China)
CREATE TABLE IF NOT EXISTS pork_gold.fact_china_imports (
  date_key           INT UNSIGNED NOT NULL,
  partner_key        SMALLINT UNSIGNED NOT NULL,
  product_key        SMALLINT UNSIGNED NOT NULL,
  tonnes             DECIMAL(14,3) NULL,
  value_usd          DECIMAL(18,2) NOT NULL,
  unit_value_usd_kg  DECIMAL(10,4) NULL,
  share_pct          DECIMAL(7,4)  NULL COMMENT '% del volumen total del HS en el mes',
  PRIMARY KEY (date_key, partner_key, product_key),
  KEY ix_fci_partner (partner_key),
  KEY ix_fci_product (product_key),
  CONSTRAINT fk_fci_date    FOREIGN KEY (date_key)    REFERENCES pork_gold.dim_date (date_key),
  CONSTRAINT fk_fci_partner FOREIGN KEY (partner_key) REFERENCES pork_gold.dim_country (country_key),
  CONSTRAINT fk_fci_product FOREIGN KEY (product_key) REFERENCES pork_gold.dim_product (product_key)
) ENGINE=InnoDB;

-- Grano: proveedor–producto–escenario
CREATE TABLE IF NOT EXISTS pork_gold.fact_landed_cost (
  scenario_key        TINYINT UNSIGNED NOT NULL,
  supplier_key        SMALLINT UNSIGNED NOT NULL,
  product_key         SMALLINT UNSIGNED NOT NULL,
  fob_usd_kg          DECIMAL(10,4) NOT NULL,
  freight_usd_kg      DECIMAL(10,4) NOT NULL,
  insurance_usd_kg    DECIMAL(10,4) NOT NULL,
  cif_usd_kg          DECIMAL(10,4) NOT NULL,
  total_duty_pct      DECIMAL(7,2)  NOT NULL,
  landed_usd_kg       DECIMAL(10,4) NOT NULL,
  gap_vs_best_usd_kg  DECIMAL(10,4) NULL,
  PRIMARY KEY (scenario_key, supplier_key, product_key),
  CONSTRAINT fk_flc_scenario FOREIGN KEY (scenario_key) REFERENCES pork_gold.dim_scenario (scenario_key),
  CONSTRAINT fk_flc_supplier FOREIGN KEY (supplier_key) REFERENCES pork_gold.dim_country (country_key),
  CONSTRAINT fk_flc_product  FOREIGN KEY (product_key)  REFERENCES pork_gold.dim_product (product_key)
) ENGINE=InnoDB;

-- Grano: escenario–año (0 = inversión inicial)
CREATE TABLE IF NOT EXISTS pork_gold.fact_scenario_cashflow (
  scenario_key    TINYINT UNSIGNED NOT NULL,
  year_n          TINYINT UNSIGNED NOT NULL,
  tonnes          DECIMAL(12,2) NOT NULL DEFAULT 0,
  capex           DECIMAL(16,2) NOT NULL DEFAULT 0,
  revenue         DECIMAL(16,2) NOT NULL DEFAULT 0,
  opex            DECIMAL(16,2) NOT NULL DEFAULT 0,
  net_cashflow    DECIMAL(16,2) NOT NULL,
  discounted_cf   DECIMAL(16,2) NOT NULL,
  cumulative_dcf  DECIMAL(16,2) NOT NULL,
  PRIMARY KEY (scenario_key, year_n),
  CONSTRAINT ck_fsc_year CHECK (year_n <= 10),
  CONSTRAINT fk_fsc_scenario FOREIGN KEY (scenario_key) REFERENCES pork_gold.dim_scenario (scenario_key)
) ENGINE=InnoDB;

-- Grano: escenario (KPIs ya calculados en Python y probados con pytest)
CREATE TABLE IF NOT EXISTS pork_gold.fact_scenario_result (
  scenario_key      TINYINT UNSIGNED NOT NULL,
  npv_usd           DECIMAL(16,2) NOT NULL,
  irr_pct           DECIMAL(7,2)  NULL COMMENT 'NULL si no existe TIR',
  payback_years     DECIMAL(5,2)  NULL COMMENT 'NULL si no se recupera en el horizonte',
  breakeven_tonnes  DECIMAL(12,2) NULL,
  fx_usd            DECIMAL(16,2) NOT NULL DEFAULT 0 COMMENT 'divisas acumuladas',
  jobs              INT UNSIGNED  NOT NULL DEFAULT 0,
  PRIMARY KEY (scenario_key),
  CONSTRAINT fk_fsr_scenario FOREIGN KEY (scenario_key) REFERENCES pork_gold.dim_scenario (scenario_key)
) ENGINE=InnoDB;

-- Grano: simulación (Capa 3)
CREATE TABLE IF NOT EXISTS pork_gold.fact_monte_carlo (
  run_tag       VARCHAR(30) NOT NULL COMMENT 'identifica la corrida (fecha + semilla)',
  sim_id        INT UNSIGNED NOT NULL,
  scenario_key  TINYINT UNSIGNED NOT NULL,
  npv_usd       DECIMAL(16,2) NOT NULL,
  irr_pct       DECIMAL(7,2)  NULL,
  PRIMARY KEY (run_tag, scenario_key, sim_id),
  CONSTRAINT fk_fmc_scenario FOREIGN KEY (scenario_key) REFERENCES pork_gold.dim_scenario (scenario_key)
) ENGINE=InnoDB;

-- Grano: provincia–enfermedad–mes
CREATE TABLE IF NOT EXISTS pork_gold.fact_sanitary_cases (
  date_key      INT UNSIGNED NOT NULL,
  province_key  TINYINT UNSIGNED NOT NULL,
  disease       VARCHAR(4) NOT NULL,
  outbreaks     INT UNSIGNED NOT NULL DEFAULT 0,
  cases         INT UNSIGNED NOT NULL DEFAULT 0,
  PRIMARY KEY (date_key, province_key, disease),
  CONSTRAINT fk_fsan_date     FOREIGN KEY (date_key)     REFERENCES pork_gold.dim_date (date_key),
  CONSTRAINT fk_fsan_province FOREIGN KEY (province_key) REFERENCES pork_gold.dim_province (province_key)
) ENGINE=InnoDB;

-- ---------- dim_date: 2018-01 a 2032-12, un registro por mes ----------
INSERT IGNORE INTO pork_gold.dim_date
  (date_key, date, year, quarter, month, month_name_es, year_month_label, months_from_us_cut, months_from_eu_cut)
WITH RECURSIVE months AS (
  SELECT DATE('2018-01-01') AS d
  UNION ALL
  SELECT DATE_ADD(d, INTERVAL 1 MONTH) FROM months WHERE d < '2032-12-01'
)
SELECT
  CAST(DATE_FORMAT(d, '%Y%m%d') AS UNSIGNED),
  d, YEAR(d), QUARTER(d), MONTH(d),
  ELT(MONTH(d), 'enero','febrero','marzo','abril','mayo','junio','julio',
                'agosto','septiembre','octubre','noviembre','diciembre'),
  DATE_FORMAT(d, '%Y-%m'),
  TIMESTAMPDIFF(MONTH, '2025-03-01', d),
  TIMESTAMPDIFF(MONTH, '2025-09-01', d)
FROM months;
