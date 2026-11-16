-- =====================================================================
-- 008 · Auditoría de corridas del pipeline completo
-- Una fila por corrida (etl_run) y una por etapa (etl_run_stage).
-- Vive en bronze junto a extract_batch: es metadato operativo, no dato de negocio.
-- =====================================================================
CREATE TABLE IF NOT EXISTS pork_bronze.etl_run (
  run_id       BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  started_at   DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  finished_at  DATETIME(3) NULL,
  status       ENUM('running','ok','failed','aborted') NOT NULL DEFAULT 'running'
               COMMENT 'aborted = la corrida murió sin cerrar (se detecta en la siguiente)',
  trigger_src  VARCHAR(30) NOT NULL DEFAULT 'manual' COMMENT 'manual, programado, pytest',
  stages       VARCHAR(300) NOT NULL COMMENT 'etapas pedidas, en orden',
  host         VARCHAR(80) NULL,
  PRIMARY KEY (run_id),
  KEY ix_run_status (status, started_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS pork_bronze.etl_run_stage (
  run_id       BIGINT UNSIGNED NOT NULL,
  stage_order  TINYINT UNSIGNED NOT NULL,
  stage        VARCHAR(40) NOT NULL,
  status       ENUM('ok','failed','skipped') NOT NULL,
  started_at   DATETIME(3) NULL,
  finished_at  DATETIME(3) NULL,
  duration_s   DECIMAL(9,2) NULL,
  exit_code    SMALLINT NULL,
  output_tail  TEXT NULL COMMENT 'últimas líneas de la salida (la salida completa queda en logs/runs/)',
  PRIMARY KEY (run_id, stage_order),
  CONSTRAINT fk_stage_run FOREIGN KEY (run_id) REFERENCES pork_bronze.etl_run (run_id) ON DELETE CASCADE
) ENGINE=InnoDB;
