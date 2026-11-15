-- =====================================================================
-- 002 · Marcas de calidad en silver.trade_flow
-- Las filas dudosas NO se borran: se marcan. Gold decide cómo usarlas
-- (por ejemplo, excluir atípicos del precio promedio pero no del volumen).
-- SET permite varias marcas a la vez en una sola columna.
-- =====================================================================
ALTER TABLE pork_silver.trade_flow
  ADD COLUMN quality_flag SET('outlier_unit_value','missing_weight','weight_estimated_by_source')
      NULL DEFAULT NULL COMMENT 'NULL = sin observaciones' AFTER value_usd;
