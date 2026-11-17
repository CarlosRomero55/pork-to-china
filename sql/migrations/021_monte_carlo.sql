-- =====================================================================
-- 021 · Resultados del Monte Carlo (Fase 14.3) · los escribe src/monte_carlo.py
-- =====================================================================
CREATE TABLE IF NOT EXISTS pork_gold.fact_mc_summary (
  scenario_key  TINYINT UNSIGNED NOT NULL,
  n_draws       INT UNSIGNED NOT NULL,
  p_npv_pos     DOUBLE NOT NULL COMMENT 'probabilidad de VAN > 0',
  npv_mean      DOUBLE NOT NULL,
  npv_p05       DOUBLE NOT NULL,
  npv_p50       DOUBLE NOT NULL,
  npv_p95       DOUBLE NOT NULL,
  npv_base      DOUBLE NOT NULL COMMENT 'VAN con todos los supuestos en base (debe igualar fact_scenario_result)',
  PRIMARY KEY (scenario_key)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS pork_gold.fact_mc_hist (
  scenario_key  TINYINT UNSIGNED NOT NULL,
  bin           TINYINT UNSIGNED NOT NULL,
  bin_from      DOUBLE NOT NULL,
  bin_to        DOUBLE NOT NULL,
  n             INT UNSIGNED NOT NULL,
  PRIMARY KEY (scenario_key, bin)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS pork_gold.fact_mc_tornado (
  scenario_key  TINYINT UNSIGNED NOT NULL,
  assumption    VARCHAR(40)  NOT NULL,
  label_es      VARCHAR(60)  NOT NULL,
  npv_at_min    DOUBLE NOT NULL COMMENT 'VAN con este supuesto en su mínimo y los demás en base',
  npv_at_max    DOUBLE NOT NULL,
  swing         DOUBLE NOT NULL,
  spearman      DOUBLE NOT NULL COMMENT 'correlación de rangos entre el supuesto sorteado y el VAN',
  PRIMARY KEY (scenario_key, assumption)
) ENGINE=InnoDB;
