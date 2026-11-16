-- =====================================================================
-- 014 · Vistas para la API (Fase 11)
-- La API usa pork_bi, que solo tiene SELECT sobre pork_gold (mínimo privilegio). En vez de darle
-- permisos sobre silver o bronze, se exponen en gold dos vistas con lo justo. Las vistas corren con
-- los permisos de quien las creó (pork_etl, SQL SECURITY DEFINER), así pork_bi lee solo esto.
-- =====================================================================

-- Valor de cada supuesto en cada escenario (lo que /simulate necesita para recalcular)
CREATE OR REPLACE SQL SECURITY DEFINER VIEW pork_gold.v_scenario_params AS
SELECT sa.scenario_id AS scenario_key, a.name, a.version, a.unit,
       CASE sa.which_value WHEN 'min' THEN a.value_min WHEN 'max' THEN a.value_max ELSE a.value_base END AS value,
       sa.which_value, a.value_min, a.value_base, a.value_max
FROM pork_silver.scenario_assumption sa
JOIN pork_silver.assumption a ON a.assumption_id = sa.assumption_id;

-- Última corrida real del pipeline (para /health); excluye las corridas de prueba
CREATE OR REPLACE SQL SECURITY DEFINER VIEW pork_gold.v_last_pipeline_run AS
SELECT run_id, started_at, finished_at, status
FROM pork_bronze.etl_run
WHERE trigger_src <> 'pytest'
ORDER BY run_id DESC
LIMIT 1;
