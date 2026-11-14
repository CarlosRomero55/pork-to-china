-- =====================================================================
-- 01_bronze.sql · Capa BRONZE · datos crudos e inmutables
-- Regla: aquí NUNCA se hace UPDATE ni DELETE. Una corrección de la fuente
-- entra como fila nueva (otro batch_id). Así se puede reconstruir el
-- análisis "tal como se veía" en cualquier fecha.
-- Idempotente: se puede ejecutar varias veces sin error.
-- =====================================================================

CREATE DATABASE IF NOT EXISTS pork_bronze
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

-- Cada ejecución de un extractor = un lote (batch)
CREATE TABLE IF NOT EXISTS pork_bronze.extract_batch (
  batch_id     BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  source_name  VARCHAR(40)  NOT NULL COMMENT 'comtrade, gacc, usda_psd, faostat, mofcom, agrocalidad...',
  started_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finished_at  DATETIME     NULL,
  status       ENUM('running','ok','failed') NOT NULL DEFAULT 'running',
  rows_loaded  INT UNSIGNED NOT NULL DEFAULT 0,
  params       JSON         NULL COMMENT 'qué se pidió (reporter, años, HS...)',
  error_msg    TEXT         NULL,
  PRIMARY KEY (batch_id),
  KEY ix_batch_source_time (source_name, started_at)
) ENGINE=InnoDB COMMENT='Lotes de extracción (auditoría)';

-- Respuestas de APIs, guardadas tal cual
CREATE TABLE IF NOT EXISTS pork_bronze.raw_api_response (
  raw_id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  batch_id        BIGINT UNSIGNED NOT NULL,
  source_name     VARCHAR(40)  NOT NULL,
  endpoint        VARCHAR(255) NOT NULL,
  request_params  JSON         NULL,
  payload         JSON         NOT NULL COMMENT 'respuesta intacta',
  payload_hash    CHAR(64)     NOT NULL COMMENT 'SHA-256 del payload: evita duplicar la misma respuesta',
  extracted_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (raw_id),
  UNIQUE KEY uq_raw_api_hash (payload_hash),
  KEY ix_raw_api_source_time (source_name, extracted_at),
  CONSTRAINT fk_raw_api_batch FOREIGN KEY (batch_id)
    REFERENCES pork_bronze.extract_batch (batch_id)
) ENGINE=InnoDB COMMENT='Respuestas crudas de APIs';

-- Archivos descargados (Excel de GACC, PDF de Agrocalidad, anuncios de MOFCOM...)
CREATE TABLE IF NOT EXISTS pork_bronze.raw_file (
  file_id       BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  batch_id      BIGINT UNSIGNED NOT NULL,
  source_name   VARCHAR(40)  NOT NULL,
  file_name     VARCHAR(255) NOT NULL,
  stored_path   VARCHAR(500) NOT NULL COMMENT 'ruta relativa en data/raw/',
  source_url    VARCHAR(1000) NULL,
  file_hash     CHAR(64)     NOT NULL,
  extracted_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (file_id),
  UNIQUE KEY uq_raw_file_hash (file_hash),
  CONSTRAINT fk_raw_file_batch FOREIGN KEY (batch_id)
    REFERENCES pork_bronze.extract_batch (batch_id)
) ENGINE=InnoDB COMMENT='Registro de archivos crudos';

-- Filas de tablas extraídas de PDFs, sin interpretar
CREATE TABLE IF NOT EXISTS pork_bronze.raw_pdf_table (
  row_id      BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  file_id     BIGINT UNSIGNED NOT NULL,
  page_no     SMALLINT UNSIGNED NOT NULL,
  table_no    TINYINT UNSIGNED NOT NULL DEFAULT 1,
  row_no      SMALLINT UNSIGNED NOT NULL,
  row_values  JSON NOT NULL COMMENT 'fila tal como salió del PDF',
  PRIMARY KEY (row_id),
  UNIQUE KEY uq_pdf_row (file_id, page_no, table_no, row_no),
  CONSTRAINT fk_pdf_row_file FOREIGN KEY (file_id)
    REFERENCES pork_bronze.raw_file (file_id)
) ENGINE=InnoDB COMMENT='Tablas crudas extraídas de PDFs';
