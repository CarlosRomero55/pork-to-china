-- =====================================================================
-- 011 · Supuestos del costo puesto en China (landed cost) · versionados (mín · base · máx)
--
-- Flete refrigerado (contenedor reefer de 40 pies) por ruta hacia China. No hay un índice público de
-- tarifas reefer hacia China; se usan referencias de mercado 2026 y se deja un rango amplio:
--   · Contenedor reefer 40' China–Chile: USD 4.500–7.500, ~26 t (Delpa Group, 2026).
--   · Reefer 40' China–Europa/Mediterráneo: USD 4.300–5.600 (Gerudo Logistics, jun-2026).
--   · El reefer cuesta 50–100% más que el contenedor seco; un 40' lleva 20–24 t (Gerudo Logistics).
-- La ruta hacia China es de retorno (backhaul) para la carga seca, pero no necesariamente para la
-- refrigerada (fruta chilena, carne): por eso no se usan las tarifas secas, que son mucho más bajas.
-- =====================================================================
INSERT IGNORE INTO pork_silver.source (name, publisher, url) VALUES
 ('delpa_group', 'Delpa Group · costo de flete marítimo China–Chile 2026', 'https://www.delpagroup.com/en/guias/costo-flete-maritimo-china-chile'),
 ('gerudo_logistics', 'Gerudo Logistics · costos de contenedor reefer 2026', 'https://www.gerudologistics.com/shipping-guides/reefer-container-shipping-cost-from-china');

INSERT IGNORE INTO pork_silver.assumption (name, version, value_min, value_base, value_max, unit, source_id, rationale)
SELECT x.name, 1, x.vmin, x.vbase, x.vmax, x.unit, s.source_id, x.why
FROM (
  SELECT 'freight_reefer40_pacific' name, 3000 vmin, 4500 vbase, 7500 vmax, 'USD/contenedor' unit, 'delpa_group' src,
         'Pacífico sudamericano → China (Ecuador, Chile, Perú). Referencia: reefer 40'' China–Chile USD 4.500–7.500. Supuesto: simétrico.' why
  UNION ALL SELECT 'freight_reefer40_brazil', 3500, 5500, 8000, 'USD/contenedor', 'delpa_group',
         'Atlántico sudamericano → China (Brasil): ruta más larga que el Pacífico. Supuesto con base en la ruta del Pacífico +20%.'
  UNION ALL SELECT 'freight_reefer40_europe', 2500, 4300, 5600, 'USD/contenedor', 'gerudo_logistics',
         'Europa → China. Referencia: reefer 40'' China–Europa USD 4.300–5.600 (jun-2026); el mínimo refleja que es ruta de retorno.'
  UNION ALL SELECT 'freight_reefer40_north_america', 2000, 3500, 5000, 'USD/contenedor', 'gerudo_logistics',
         'Norteamérica → China. Supuesto: reefer = 2 veces el flete seco (que es bajo en retorno), rango amplio.'
  UNION ALL SELECT 'reefer_payload_t', 20, 24, 26, 't/contenedor', 'gerudo_logistics',
         'Carga neta de un reefer de 40'': 20–24 t según el empaque (Gerudo); hasta ~26 t (Delpa).'
  UNION ALL SELECT 'cargo_insurance_pct', 0.2, 0.3, 0.5, '% del valor CIF', NULL,
         'Supuesto de práctica comercial; sin fuente específica. Impacto en el resultado: < 0,01 USD/kg.'
  UNION ALL SELECT 'ecuador_fob_usd_kg_offal', 1.50, 1.60, 1.86, 'USD/kg', NULL,
         'Ecuador como tomador de precio: base = FOB de Chile en vísceras congeladas 020649 (2025, consulta q08); mín = Reino Unido/Canadá; máx = España.'
) x
LEFT JOIN pork_silver.source s ON s.name = x.src;

-- La producción de Ecuador sembrada en la Fase 0 (230–240 mil t) quedó por encima de las cifras con fuente
-- que hoy están en silver (ASPE/MAG). No se sobrescribe: se crea la versión 2.
INSERT IGNORE INTO pork_silver.assumption (name, version, value_min, value_base, value_max, unit, source_id, rationale)
SELECT 'ecuador_pork_production', 2, 213000, 223650, 240000, 't/año', s.source_id,
       'v2: mín = ASPE 2023 (213 mil t); base = ASPE 2024 estimado (+5%); máx = Aprobal 2025 (240 mil t, valor de la v1).'
FROM pork_silver.source s WHERE s.name = 'aspe';
