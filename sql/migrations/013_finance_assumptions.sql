-- =====================================================================
-- 013 · Supuestos del flujo de caja de AgroPorc (adecuación de una planta existente)
-- USD reales (sin inflación), horizonte de 10 años, año 0 = 2026. Todos versionados (mín · base · máx)
-- y asignados con su valor base a los 24 escenarios; el simulador del tablero (Fase 12) los moverá.
--
-- Fuentes:
--   Túnel de congelación −35 °C de 50 m² (20–25 t/día): USD 52.000–70.000 (Haocool, 2026).
--   Cámara −18 °C de 400 m² (360–400 t): USD 115.000–150.000 llave en mano (Haocool, 2026).
--   Energía de congelación mecánica: USD 0,008–0,025 por libra (Baoxue, 2026, precios de EE. UU.).
--   Impuesto a la renta de sociedades 25% (SRI / Primicias, 2025) + 15% de participación de trabajadores
--   → carga efectiva 1 − 0,85 × 0,75 = 36,25% (≈ 36% según De la Torre e Hidalgo, vía El Oriente 2026).
--   Sin fuente (supuestos): adecuación sanitaria, habilitación para China, costos de proceso, logística,
--   costos fijos, empleos y el VALOR LOCAL DE LA VÍSCERA (el modelo calcula el máximo que tolera el proyecto).
-- =====================================================================
INSERT IGNORE INTO pork_silver.source (name, publisher, url) VALUES
 ('haocool', 'Haocool Refrigeration · costos de cámaras y túneles de frío 2026', 'https://www.coldstorageinchina.com/minus-35-blast-freezer-cost-for-food-factory/'),
 ('baoxue', 'Baoxue Refrigeration · Blast Freezer Tunnel Guide 2026', 'https://www.bxfreezing.com/blast-freezer-tunnel-guide-how-to-choose-install-optimize-for-2026'),
 ('sri_primicias', 'Primicias · impuesto a la renta de sociedades (SRI)', 'https://primicias.ec/economia/declaracion-impuesto-renta-abril2025-sociedades-empresas-rimpe-emprendedores-92961');

INSERT IGNORE INTO pork_silver.assumption (name, version, value_min, value_base, value_max, unit, source_id, rationale)
SELECT x.name, 1, x.vmin, x.vbase, x.vmax, x.unit, s.source_id, x.why
FROM (
  SELECT 'capex_blast_freezer' name, 52000 vmin, 70000 vbase, 120000 vmax, 'USD' unit, 'haocool' src,
         'Túnel −35 °C de 50 m², 20–25 t/día (≈ 5.000 t/año en 250 días). Máx incluye importación e instalación.' why
  UNION ALL SELECT 'capex_cold_storage', 115000, 135000, 150000, 'USD', 'haocool',
         'Cámara −18 °C de 400 m² (360–400 t ≈ 1 mes de producción a 5.000 t/año).'
  UNION ALL SELECT 'capex_plant_upgrade', 150000, 250000, 400000, 'USD', NULL,
         'Adecuación sanitaria: línea de limpieza y recorte, detector de metales, empaque. Supuesto sin fuente.'
  UNION ALL SELECT 'capex_china_registration', 50000, 100000, 200000, 'USD', NULL,
         'Habilitación para China: auditorías, consultoría, laboratorio, visita de inspección y registro GACC. Supuesto sin fuente.'
  UNION ALL SELECT 'offal_local_value_usd_kg', 0.60, 0.90, 1.20, 'USD/kg', NULL,
         'Valor de la víscera en el mercado local (costo de oportunidad de exportarla). SIN FUENTE: el modelo calcula el máximo que tolera el proyecto (VAN = 0).'
  UNION ALL SELECT 'processing_cost_usd_kg', 0.10, 0.15, 0.20, 'USD/kg', NULL,
         'Limpieza, recorte, cartón y etiqueta en chino. Supuesto sin fuente.'
  UNION ALL SELECT 'freezing_cost_usd_kg', 0.03, 0.05, 0.08, 'USD/kg', 'baoxue',
         'Energía de congelación y almacenamiento. Referencia: USD 0,018–0,055/kg en túneles mecánicos (EE. UU.).'
  UNION ALL SELECT 'export_logistics_usd_kg', 0.03, 0.05, 0.07, 'USD/kg', NULL,
         'Transporte a Guayaquil, manejo portuario y certificado de exportación (≈ USD 800–1.500 por contenedor de 24 t). Supuesto.'
  UNION ALL SELECT 'fixed_cost_usd_year', 60000, 100000, 150000, 'USD/año', NULL,
         'Jefe de exportación, aseguramiento de calidad, auditorías y laboratorio; desde el primer año de exportación. Supuesto.'
  UNION ALL SELECT 'effective_tax_pct', 36.25, 36.25, 36.25, '%', 'sri_primicias',
         'Impuesto a la renta 25% + participación de trabajadores 15%: 1 − 0,85 × 0,75. Sin arrastre de pérdidas (conservador).'
  UNION ALL SELECT 'depreciation_years', 10, 10, 10, 'años', NULL,
         'Depreciación lineal de toda la inversión en 10 años.'
  UNION ALL SELECT 'working_capital_months', 1, 2, 3, 'meses de costo variable', NULL,
         'Capital de trabajo (inventario y cuentas por cobrar); se recupera en el año 10. Supuesto.'
  UNION ALL SELECT 'jobs_fixed', 6, 8, 12, 'empleos', NULL,
         'Empleos directos fijos de la operación de exportación. Supuesto.'
  UNION ALL SELECT 'jobs_per_1000t', 2, 3, 4, 'empleos por 1.000 t', NULL,
         'Empleos directos variables de proceso y frío. Supuesto.'
) x
LEFT JOIN pork_silver.source s ON s.name = x.src;

-- Producción de Ecuador v3: ASPE reporta 230 mil t en 2025 y estima 245 mil t en 2026 (El Universo, 2026).
INSERT IGNORE INTO pork_silver.source (name, publisher, url) VALUES
 ('el_universo', 'Diario El Universo', 'https://www.eluniverso.com/noticias/economia/consumo-carne-cerdo-precios-mercado-local-exportaciones-asia-ecuador-2026-nota/');
INSERT IGNORE INTO pork_silver.assumption (name, version, value_min, value_base, value_max, unit, source_id, rationale)
SELECT 'ecuador_pork_production', 3, 213000, 230000, 245000, 't/año', s.source_id,
       'v3: mín = ASPE 2023 (213 mil t); base = ASPE 2025 (230 mil t); máx = ASPE estimado 2026 (245 mil t), vía El Universo.'
FROM pork_silver.source s WHERE s.name = 'el_universo';

-- Todos los escenarios usan el valor base de estos supuestos (y la tasa de descuento base, 12%)
INSERT IGNORE INTO pork_silver.scenario_assumption (scenario_id, assumption_id, which_value)
SELECT s.scenario_id, a.assumption_id, 'base'
FROM pork_silver.scenario s
JOIN pork_silver.assumption a
  ON a.name IN ('capex_blast_freezer', 'capex_cold_storage', 'capex_plant_upgrade', 'capex_china_registration',
                'offal_local_value_usd_kg', 'processing_cost_usd_kg', 'freezing_cost_usd_kg', 'export_logistics_usd_kg',
                'fixed_cost_usd_year', 'effective_tax_pct', 'depreciation_years', 'working_capital_months',
                'jobs_fixed', 'jobs_per_1000t', 'discount_rate', 'ecuador_fob_usd_kg_offal');

ALTER TABLE pork_gold.fact_scenario_result
  ADD COLUMN discounted_payback_years DECIMAL(5,2) NULL COMMENT 'NULL si no se recupera en el horizonte' AFTER payback_years,
  ADD COLUMN breakeven_offal_usd_kg   DECIMAL(8,3) NULL
      COMMENT 'valor local máximo de la víscera con el que VAN = 0 (NULL si nunca exporta)' AFTER breakeven_tonnes;
