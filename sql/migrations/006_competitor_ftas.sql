-- =====================================================================
-- 006 · TLC de competidores con China (carne y vísceras de cerdo, 0203 y 0206)
--   Chile: TLC vigente desde 2006; el cerdo chileno entra con arancel cero
--          (ChileCarne vía Xinhua, sep-2019; Radio Agricultura, sep-2019).
--   Costa Rica: TLC vigente desde 2011; "los productos de carne porcina se encuentran
--          en libre comercio, en el marco del tratado" (EY vía Revista EyN, 2019).
--   Se cargan con 0% desde el inicio del horizonte (2018). Las líneas 0210 no se
--   verificaron y quedan con NMF.
-- Además: arancel efectivo en gold (preferencial cuando existe) y marca de acceso real.
-- =====================================================================
INSERT IGNORE INTO pork_silver.source (name, publisher, url) VALUES
 ('chilecarne', 'ChileCarne (Asociación de Exportadores de Carnes de Chile) vía Xinhua', 'https://bccci.net/?p=19263'),
 ('ey_costa_rica', 'EY vía Revista EyN (Costa Rica)', 'https://www.revistaeyn.com/centroamericaymundo/ey-peste-porcina-en-china-es-una-oportunidad-comercial-para-costa-rica-MAEN1316390');

INSERT IGNORE INTO pork_silver.trade_measure
 (imposing_id, target_id, target_group_id, target_company, hs_code, measure_type, rate_pct, valid_from, valid_to, source_id, notes)
SELECT cn.country_id, t.country_id, NULL, NULL, p.hs_code, 'preferential', 0.00, '2018-01-01', '9999-12-31', s.source_id, x.notes
FROM (
  SELECT 'CHL' iso3, 'chilecarne' src, 'TLC Chile–China (2006): cerdo con arancel cero' notes UNION ALL
  SELECT 'CRI', 'ey_costa_rica', 'TLC Costa Rica–China (2011): cerdo en libre comercio'
) x
JOIN pork_silver.hs_product p ON p.hs4 IN ('0203','0206')
JOIN pork_silver.country cn ON cn.iso3 = 'CHN'
JOIN pork_silver.country t  ON t.iso3  = x.iso3
JOIN pork_silver.source  s  ON s.name  = x.src;

-- Arancel efectivo: con acuerdo se usa el preferencial; sin acuerdo, el NMF
ALTER TABLE pork_gold.fact_tariff_applied
  ADD COLUMN effective_min_pct DECIMAL(7,2) NOT NULL DEFAULT 0
      COMMENT 'arancel que realmente pagaría: preferencial si hay acuerdo, si no NMF (+ adicionales + antidumping mín.)',
  ADD COLUMN effective_max_pct DECIMAL(7,2) NOT NULL DEFAULT 0;

-- Acceso sanitario observado en los datos: el país le vendió cerdo a China en los últimos
-- 24 meses con datos. Un acuerdo arancelario no sirve sin este acceso (caso Ecuador).
ALTER TABLE pork_gold.dim_country
  ADD COLUMN exports_pork_to_china BOOLEAN NOT NULL DEFAULT FALSE
      COMMENT 'TRUE si hay ventas de cerdo a China en los últimos 24 meses con datos';
