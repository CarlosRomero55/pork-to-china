-- =====================================================================
-- 010 · Cobertura mensual de los datos espejo + vistas del tablero (Streamlit las lee con pork_bi)
--
-- Los exportadores publican con rezagos distintos: en 2026-09 solo habían reportado Brasil y Chile,
-- y Chile "lideraba" las vísceras. build_gold.py calcula esta tabla: un mes es COMPLETO si reportaron
-- los proveedores relevantes (≥ 2% del volumen de los 12 meses anteriores), tolerando que falte uno
-- (p. ej. Francia, que no reporta desde enero de 2026). Contar todos los países no sirve: Alemania y
-- Polonia reportan de forma esporádica con volúmenes mínimos e inflan lo "esperado".
-- =====================================================================
CREATE TABLE IF NOT EXISTS pork_gold.mirror_coverage (
  date_key        INT UNSIGNED NOT NULL,
  reporters       TINYINT UNSIGNED NOT NULL COMMENT 'exportadores con datos ese mes',
  major_expected  TINYINT UNSIGNED NOT NULL COMMENT 'proveedores con ≥ 2% del volumen en los 12 meses previos',
  major_reported  TINYINT UNSIGNED NOT NULL,
  missing_major   VARCHAR(60) NULL COMMENT 'ISO3 de los relevantes que faltan',
  is_complete     BOOLEAN NOT NULL,
  PRIMARY KEY (date_key),
  CONSTRAINT fk_cov_date FOREIGN KEY (date_key) REFERENCES pork_gold.dim_date (date_key)
) ENGINE=InnoDB;

-- 1. Ventas mensuales de cada proveedor a China (espejo, FOB) con todo lo que el tablero filtra
CREATE OR REPLACE VIEW pork_gold.v_dash_supplier_monthly AS
SELECT d.date, d.year, d.month, d.year_month_label, d.months_from_us_cut,
       c.iso3, c.name_es AS supplier, c.supplier_bloc, c.exports_pork_to_china AS has_access,
       p.hs_code, p.product_group_es AS product_group, p.description_es, p.is_sam,
       f.tonnes, f.value_usd,
       CASE WHEN f.tonnes > 0 THEN f.value_usd / (1000 * f.tonnes) END AS fob_usd_kg,
       f.is_outlier, cov.is_complete AS month_is_complete
FROM pork_gold.fact_china_imports f
JOIN pork_gold.dim_date d    ON d.date_key = f.date_key
JOIN pork_gold.dim_country c ON c.country_key = f.partner_key
JOIN pork_gold.dim_product p ON p.product_key = f.product_key
JOIN pork_gold.mirror_coverage cov ON cov.date_key = f.date_key
WHERE f.basis = 'mirror';

-- 2. Arancel efectivo por mes, origen y línea, con nombres y acceso
CREATE OR REPLACE VIEW pork_gold.v_dash_tariff AS
SELECT d.date, d.year, d.year_month_label, c.iso3, c.name_es AS origin, c.supplier_bloc,
       c.exports_pork_to_china AS has_access, p.hs_code, p.product_group_es AS product_group, p.is_sam,
       t.mfn_pct, t.preferential_pct, t.additional_pct, t.antidumping_min_pct, t.antidumping_max_pct,
       t.effective_min_pct, t.effective_max_pct
FROM pork_gold.fact_tariff_applied t
JOIN pork_gold.dim_date d    ON d.date_key = t.date_key
JOIN pork_gold.dim_country c ON c.country_key = t.origin_key
JOIN pork_gold.dim_product p ON p.product_key = t.product_key;

-- 3. Balance de China (USDA)
CREATE OR REPLACE VIEW pork_gold.v_dash_china_balance AS
SELECT market_year, production_kt, imports_kt, exports_kt, consumption_kt, ending_stocks_kt,
       import_share_pct, self_sufficiency_pct, is_projection
FROM pork_gold.fact_market_balance
WHERE psd_code = 'CH';

-- 4. Tamaño del SAM por año (solo meses completos)
CREATE OR REPLACE VIEW pork_gold.v_dash_sam_yearly AS
SELECT year,
       COUNT(DISTINCT month)                                                   AS months,
       SUM(tonnes)                                                             AS sam_tonnes,
       SUM(value_usd)                                                          AS sam_usd,
       SUM(value_usd) / (1000 * SUM(tonnes))                                   AS fob_usd_kg,
       100 * SUM(CASE WHEN iso3 IN ('USA', 'CAN') THEN tonnes ELSE 0 END) / SUM(tonnes) AS pct_usa_can
FROM pork_gold.v_dash_supplier_monthly
WHERE is_sam AND month_is_complete
GROUP BY year;
