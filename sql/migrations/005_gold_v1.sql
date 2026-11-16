-- =====================================================================
-- 005 · Gold v1: importaciones de China con su base (directo o espejo)
--       y arancel aplicado por mes × origen × línea HS
-- Las tablas de hechos se reconstruyen completas en cada corrida (build_gold.py).
-- =====================================================================

-- Directo (lo que reporta China, CIF) y espejo (lo que declaran los exportadores, FOB)
-- se guardan como filas distintas: nunca se suman ni se mezclan (ADR-008).
ALTER TABLE pork_gold.fact_china_imports
  ADD COLUMN basis ENUM('direct','mirror') NOT NULL DEFAULT 'direct'
      COMMENT 'direct = reporta China (CIF) · mirror = reporta el exportador (FOB)' AFTER product_key,
  ADD COLUMN is_outlier BOOLEAN NOT NULL DEFAULT FALSE
      COMMENT 'USD/kg atípico según la regla R05 de silver' AFTER share_pct,
  DROP PRIMARY KEY,
  ADD PRIMARY KEY (date_key, partner_key, product_key, basis);

-- Grano: mes × origen × línea HS. Tasa vigente el día 15 de cada mes.
CREATE TABLE IF NOT EXISTS pork_gold.fact_tariff_applied (
  date_key             INT UNSIGNED NOT NULL,
  origin_key           SMALLINT UNSIGNED NOT NULL,
  product_key          SMALLINT UNSIGNED NOT NULL,
  mfn_pct              DECIMAL(6,2) NOT NULL,
  preferential_pct     DECIMAL(6,2) NULL COMMENT 'tasa de acuerdo comercial (reemplaza al NMF); NULL = sin acuerdo',
  additional_pct       DECIMAL(6,2) NOT NULL DEFAULT 0 COMMENT 'represalias y medidas por país',
  antidumping_min_pct  DECIMAL(6,2) NULL COMMENT 'rango por empresa; NULL = sin antidumping',
  antidumping_max_pct  DECIMAL(6,2) NULL,
  total_min_pct        DECIMAL(7,2) NOT NULL COMMENT 'NMF + adicionales + antidumping mínimo',
  total_max_pct        DECIMAL(7,2) NOT NULL COMMENT 'NMF + adicionales + antidumping máximo',
  total_pref_pct       DECIMAL(7,2) NULL COMMENT 'preferencial + adicionales (si aplica el acuerdo)',
  PRIMARY KEY (date_key, origin_key, product_key),
  KEY ix_fta_origin (origin_key),
  CONSTRAINT fk_fta_date    FOREIGN KEY (date_key)    REFERENCES pork_gold.dim_date (date_key),
  CONSTRAINT fk_fta_origin  FOREIGN KEY (origin_key)  REFERENCES pork_gold.dim_country (country_key),
  CONSTRAINT fk_fta_product FOREIGN KEY (product_key) REFERENCES pork_gold.dim_product (product_key)
) ENGINE=InnoDB;

-- Serie continua de toneladas por proveedor: directo hasta 2024-12 y espejo desde 2025-01,
-- solo para los exportadores que tienen espejo (en peso, directo/espejo = 0,992 → comparable).
-- En valor NO es comparable (CIF vs FOB): por eso la vista solo expone toneladas.
CREATE OR REPLACE VIEW pork_gold.v_supplier_tonnes AS
SELECT f.date_key, f.partner_key, f.product_key, f.tonnes, f.basis
FROM pork_gold.fact_china_imports f
WHERE (f.basis = 'direct' AND f.date_key < 20250101
       AND f.partner_key IN (SELECT DISTINCT partner_key FROM pork_gold.fact_china_imports WHERE basis = 'mirror'))
   OR (f.basis = 'mirror' AND f.date_key >= 20250101);
