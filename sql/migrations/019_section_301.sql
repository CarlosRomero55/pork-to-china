-- =====================================================================
-- 019 · Represalia de la sección 301 contra el cerdo de EE. UU. (Fase 14.2, supuesto #47)
-- El 6-jul-2018 China sumó 25% por la sección 301 al 12% NMF + 25% de la 232: el cerdo de EE. UU. pagó 62%.
-- Desde marzo de 2020 la Comisión Arancelaria (SCTC) permite que cada importador pida la exclusión de la 301
-- (no de la 232). Decisión de Carlos (2026-11-17): cargarla del 6-jul-2018 al 1-mar-2020 y SUPONER que
-- desde ahí los importadores piden la exclusión (por eso 2025 sigue en 37% antes de los aranceles recíprocos).
-- 25% es la tasa base; USDA reporta 30% para algunas líneas congeladas desde 2019: se usa el valor conservador.
-- Con la medida en trade_measure, el rastreador la muestra solo: se borra el evento manual que la duplicaba.
-- =====================================================================
INSERT IGNORE INTO pork_silver.trade_measure
 (imposing_id, target_id, target_group_id, target_company, hs_code, measure_type, rate_pct, valid_from, valid_to, source_id, notes)
SELECT cn.country_id, us.country_id, NULL, NULL, p.hs_code, 'retaliatory_301', 25.00, '2018-07-06', '2020-03-01',
       s.source_id,
       'Total 62% con NMF 12% y 232. Desde mar-2020 excluible por importador (SCTC): se supone la exclusión (supuesto #47)'
FROM pork_silver.hs_product p
JOIN pork_silver.country cn ON cn.iso3 = 'CHN'
JOIN pork_silver.country us ON us.iso3 = 'USA'
JOIN pork_silver.source  s  ON s.name  = 'nhf_301_2018'
WHERE p.hs4 IN ('0203', '0206');

DELETE FROM pork_silver.policy_event
WHERE event_date = '2018-07-06' AND country_iso3 = 'USA' AND category = 'arancel';

CREATE OR REPLACE SQL SECURITY DEFINER VIEW pork_gold.v_dash_policy_events AS
SELECT pe.event_date, pe.date_precision, pe.country_iso3, COALESCE(c.name_es, pe.country_iso3) AS country_es,
       pe.category, pe.title_es, pe.detail_es, pe.effect_es, pe.its_role, 'manual' AS origin,
       s.publisher AS source, s.url
FROM pork_silver.policy_event pe
JOIN pork_silver.source s ON s.source_id = pe.source_id
LEFT JOIN pork_silver.country c ON c.iso3 = pe.country_iso3
UNION ALL
SELECT m.valid_from, 'dia',
       COALESCE(ct.iso3, CASE WHEN m.target_group_id IS NOT NULL THEN 'EU' ELSE 'WLD' END),
       COALESCE(ct.name_es, CASE WHEN m.target_group_id IS NOT NULL THEN 'Unión Europea' ELSE 'Todos los proveedores' END),
       'arancel',
       CONCAT('China: ', CASE m.measure_type
                WHEN 'mfn' THEN 'arancel NMF'
                WHEN 'retaliatory_232' THEN 'represalia por la sección 232'
                WHEN 'retaliatory_301' THEN 'represalia por la sección 301'
                WHEN 'retaliatory_fentanyl' THEN 'represalia por el arancel del fentanilo'
                WHEN 'anti_discrimination' THEN 'arancel antidiscriminación'
                WHEN 'reciprocal' THEN 'arancel recíproco'
                WHEN 'antidumping_provisional' THEN 'antidumping provisional'
                WHEN 'antidumping' THEN 'antidumping definitivo'
                ELSE m.measure_type END, ' de ',
              REPLACE(CASE WHEN MIN(m.rate_pct) = MAX(m.rate_pct) THEN TRIM(TRAILING '.' FROM TRIM(TRAILING '0' FROM CAST(MIN(m.rate_pct) AS CHAR)))
                   ELSE CONCAT(TRIM(TRAILING '.' FROM TRIM(TRAILING '0' FROM CAST(MIN(m.rate_pct) AS CHAR))), '–',
                               TRIM(TRAILING '.' FROM TRIM(TRAILING '0' FROM CAST(MAX(m.rate_pct) AS CHAR)))) END, '.', ','), '%'),
       COALESCE(MAX(m.notes), ''), 'Cambia el arancel aplicado',
       CASE WHEN m.measure_type IN ('retaliatory_232', 'retaliatory_301') AND YEAR(m.valid_from) = 2018 THEN 'corte_2018' END,
       'trade_measure', MAX(s.publisher), MAX(s.url)
FROM pork_silver.trade_measure m
JOIN pork_silver.source s ON s.source_id = m.source_id
LEFT JOIN pork_silver.country ct ON ct.country_id = m.target_id
WHERE m.imposing_id = (SELECT country_id FROM pork_silver.country WHERE iso3 = 'CHN')
  AND m.valid_from > '2018-01-01'                       -- 2018-01-01 es el inicio de la serie, no un evento
  AND m.measure_type <> 'preferential'                  -- los TLC se registran a mano; la desgravación anual no es noticia
GROUP BY m.valid_from, m.measure_type, ct.iso3, ct.name_es, m.target_group_id;
