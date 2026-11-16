-- =====================================================================
-- 012 · Mercado por escenario (TAM–SAM–SOM) · supuestos y su asignación a los 24 escenarios
--
-- Cada escenario toma el valor mín · base · máx de cada supuesto (pork_silver.scenario_assumption):
--   caso comercial A (la ventana se cierra) → mín · B (statu quo) → base · C (la ventana se abre) → máx
--   autosuficiencia china al alza → importaciones a la baja (mín) · a la baja → importaciones al alza (máx)
-- Los supuestos sin rango (rampa, capacidad base) valen igual en todos los escenarios; el simulador
-- del tablero (Fase 12) los moverá.
-- =====================================================================
INSERT IGNORE INTO pork_silver.assumption (name, version, value_min, value_base, value_max, unit, source_id, rationale)
SELECT x.name, 1, x.vmin, x.vbase, x.vmax, x.unit, NULL, x.why
FROM (
  SELECT 'china_imports_trend_pct' name, -3 vmin, 0 vbase, 3 vmax, '%/año' unit,
         'Variación anual de las importaciones chinas después de 2027 (2026–2027 siguen la proyección de USDA). Autosuficiencia al alza = −3%/año; a la baja = +3%/año. Supuesto.' why
  UNION ALL SELECT 'som_max_share_pct', 0.2, 0.3, 0.5, '% del SAM',
         'Techo de participación de un recién llegado en el SAM. A: la ventana se cierra (0,2%); B: statu quo (0,3%); C: se abre (0,5%). Chile, con 20 años en el mercado, tiene ~3,4% de las vísceras (q04). Supuesto.'
  UNION ALL SELECT 'retaliation_factor', 0, 1, 1.5, 'veces',
         'Multiplica los aranceles adicionales vigentes de China (represalias a EE. UU. y Canadá). A: se levantan (0); B: siguen (1); C: suben 50% (1,5). El antidumping a la UE no cambia. Supuesto.'
  UNION ALL SELECT 'agroporc_capacity_t', 3000, 5000, 8000, 't/año',
         'Volumen objetivo de AgroPorc en vísceras congeladas (decisión de Carlos, 2026-11-16). Base en todos los escenarios.'
  UNION ALL SELECT 'entry_ramp_y1_pct', 40, 40, 40, '% de la capacidad',
         'Primer año certificado: los importadores prueban con pocos contenedores (decisión de Carlos, rampa 40-70-100).'
  UNION ALL SELECT 'entry_ramp_y2_pct', 70, 70, 70, '% de la capacidad',
         'Segundo año certificado (rampa 40-70-100). Desde el tercero, 100%.'
  UNION ALL SELECT 'project_start_year', 2026, 2026, 2026, 'año calendario',
         'Año 0 del proyecto = 2026 (inversión). Año 1 = 2027 … año 10 = 2036.'
) x;

-- Asignación: qué valor (mín · base · máx) usa cada escenario
INSERT IGNORE INTO pork_silver.scenario_assumption (scenario_id, assumption_id, which_value)
SELECT s.scenario_id, a.assumption_id,
       CASE a.name
         WHEN 'som_max_share_pct'      THEN ELT(FIELD(s.trade_case, 'A', 'B', 'C'), 'min', 'base', 'max')
         WHEN 'retaliation_factor'     THEN ELT(FIELD(s.trade_case, 'A', 'B', 'C'), 'min', 'base', 'max')
         WHEN 'china_imports_trend_pct' THEN IF(s.china_selfsuff = 'up', 'min', 'max')
         ELSE 'base'
       END
FROM pork_silver.scenario s
JOIN pork_silver.assumption a
  ON a.name IN ('som_max_share_pct', 'retaliation_factor', 'china_imports_trend_pct', 'agroporc_capacity_t',
                'entry_ramp_y1_pct', 'entry_ramp_y2_pct', 'project_start_year');

-- Grano: escenario × año del proyecto (1–10). Toneladas de peso neto (Comtrade, base espejo).
CREATE TABLE IF NOT EXISTS pork_gold.fact_scenario_market (
  scenario_key     TINYINT UNSIGNED NOT NULL,
  year_n           TINYINT UNSIGNED NOT NULL,
  calendar_year    SMALLINT UNSIGNED NOT NULL,
  tam_t            DECIMAL(14,1) NOT NULL COMMENT 'importaciones chinas de cerdo (12 líneas HS)',
  sam_t            DECIMAL(14,1) NOT NULL COMMENT 'carne y vísceras congeladas (líneas SAM)',
  som_cap_t        DECIMAL(12,1) NOT NULL COMMENT 'techo de participación de un recién llegado',
  capacity_t       DECIMAL(12,1) NOT NULL COMMENT 'capacidad × rampa (0 antes de certificar)',
  agroporc_t       DECIMAL(12,1) NOT NULL COMMENT 'volumen vendible = mín(capacidad × rampa, techo)',
  binding          ENUM('none','capacity','market') NOT NULL COMMENT 'qué limita el volumen',
  ecuador_duty_pct DECIMAL(6,2)  NOT NULL COMMENT 'arancel de Ecuador ese año (acuerdo; NMF si no hay)',
  PRIMARY KEY (scenario_key, year_n),
  CONSTRAINT fk_fsm_scenario FOREIGN KEY (scenario_key) REFERENCES pork_gold.dim_scenario (scenario_key)
) ENGINE=InnoDB;
