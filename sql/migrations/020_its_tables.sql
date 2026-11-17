-- =====================================================================
-- 020 · Resultados de la serie de tiempo interrumpida (Fase 14.2) · los escribe src/its.py
-- =====================================================================
CREATE TABLE IF NOT EXISTS pork_gold.fact_its_series (
  model          VARCHAR(20)  NOT NULL COMMENT 'share_value (principal), share_tonnes, log_us_value',
  date           DATE         NOT NULL,
  observed       DECIMAL(14,6) NULL,
  fitted         DECIMAL(14,6) NULL,
  counterfactual DECIMAL(14,6) NULL COMMENT 'tendencia + estacionalidad sin los cortes',
  is_gap         TINYINT(1)   NOT NULL DEFAULT 0 COMMENT 'ene-feb 2020: hueco de reporte (supuesto #48)',
  PRIMARY KEY (model, date)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS pork_gold.fact_its_coef (
  model     VARCHAR(20)  NOT NULL,
  term      VARCHAR(20)  NOT NULL,
  estimate  DOUBLE       NOT NULL,
  se        DOUBLE       NOT NULL COMMENT 'Newey-West',
  t         DOUBLE       NOT NULL,
  p         DOUBLE       NOT NULL,
  ci_low    DOUBLE       NOT NULL,
  ci_high   DOUBLE       NOT NULL,
  n_obs     SMALLINT UNSIGNED NOT NULL,
  r2        DOUBLE       NOT NULL,
  nw_lags   TINYINT UNSIGNED NOT NULL,
  PRIMARY KEY (model, term)
) ENGINE=InnoDB;
