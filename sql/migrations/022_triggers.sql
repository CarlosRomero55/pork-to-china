-- =====================================================================
-- 022 · Disparadores de la recomendación (Fase 15.1) · los escribe src/recommendation.py
-- Cada fila es una condición medible que tiene que cumplirse para revisar la decisión "no invertir hoy".
-- El umbral sale del modelo (VAN = 0 en los escenarios con certificación en el año 6) o de la fuente
-- sanitaria; el valor actual sale de gold/silver en cada corrida del pipeline.
-- =====================================================================
CREATE TABLE IF NOT EXISTS pork_gold.fact_trigger (
  trigger_code    CHAR(2)       NOT NULL,
  sort_order      TINYINT UNSIGNED NOT NULL,
  role            VARCHAR(16)   NOT NULL COMMENT 'economia · acceso · complementario',
  name_es         VARCHAR(80)   NOT NULL,
  condition_es    VARCHAR(200)  NOT NULL COMMENT 'la condición escrita para una persona',
  current_value   DOUBLE        NULL     COMMENT 'NULL en los disparadores cualitativos',
  threshold       DOUBLE        NULL     COMMENT 'umbral del escenario de referencia (B-up-6)',
  threshold_min   DOUBLE        NULL     COMMENT 'rango del umbral en los 6 escenarios con certificación en el año 6',
  threshold_max   DOUBLE        NULL,
  unit            VARCHAR(16)   NULL,
  current_es      VARCHAR(400)  NOT NULL COMMENT 'el valor actual en palabras',
  status          VARCHAR(12)   NOT NULL COMMENT 'cumplido · en camino · no cumplido',
  source_es       VARCHAR(300)  NOT NULL,
  watch_es        VARCHAR(120)  NOT NULL COMMENT 'dónde se vigila: tabla y página del tablero',
  as_of           DATE          NOT NULL,
  PRIMARY KEY (trigger_code),
  CONSTRAINT chk_trigger_status CHECK (status IN ('cumplido', 'en camino', 'no cumplido')),
  CONSTRAINT chk_trigger_role CHECK (role IN ('economia', 'acceso', 'complementario'))
) ENGINE=InnoDB;
