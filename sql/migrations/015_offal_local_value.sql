-- =====================================================================
-- 015 · Valor local de la víscera v2 (Fase 13.1)
-- La v1 (0,60 · 0,90 · 1,20 USD/kg) no tenía fuente. No existe un precio oficial de víscera de cerdo
-- en Ecuador (SIPA publica cerdo en pie y en canal, no subproductos), así que la v2 se arma con
-- precios públicos minoristas e informales y un factor planta/mercado. Sigue siendo SUPUESTO, pero
-- ahora con referencias trazables:
--   · Patas de cerdo en supermercado (Quito): USD 3,32–3,90/kg (Santa María, vía Rappi, 2026)
--     y USD 4,99/kg (Friovesa, 2026); USD 4,90/kg (La Rioja, 2026).
--   · Venta directa de productor (Guayaquil): patitas USD 1,20/lb (2,65/kg) y cuero USD 1,00/lb
--     (2,20/kg), con pierna a USD 2,00/lb (anuncio clasificado, sin fecha).
--   · Factor planta/mercado 0,52: SIPA, pollo, centro de faenamiento USD 0,99/lb vs. mercado
--     USD 1,90/lb (Diario Extra, 22-oct-2026). Es otra especie: se usa solo como referencia del margen
--     de la cadena (supuesto).
-- Rango v2:
--   mín  1,14 = cuero de productor 2,20/kg × 0,52 (subproducto más barato, con margen de cadena)
--   base 1,38 = patitas de productor 2,65/kg × 0,52 (patas: lo que más compra China en vísceras)
--   máx  2,20 = cuero de productor sin descuento (la planta vende directo al detallista)
-- =====================================================================
INSERT IGNORE INTO pork_silver.source (name, publisher, url) VALUES
 ('extra_sipa_2026', 'Diario Extra · precios SIPA faenamiento vs. mercado (22-oct-2026)',
  'https://www.extra.ec/noticia/economia/dinero-alcanza-suben-precios-cerdo-res-165645.html'),
 ('retail_offal_ec_2026', 'Precios minoristas e informales de patas y cuero de cerdo en Ecuador (Rappi/Santa María, Friovesa, La Rioja, clasificados)',
  'https://friovesa.com/product/patas-cerdo-1kg/');

INSERT IGNORE INTO pork_silver.assumption (name, version, value_min, value_base, value_max, unit, source_id, rationale)
SELECT 'offal_local_value_usd_kg', 2, 1.14, 1.38, 2.20, 'USD/kg', s.source_id,
       'v2: precio de productor de cuero (2,20/kg) y patitas (2,65/kg) × factor planta/mercado 0,52 (SIPA, pollo). Máx = cuero sin descuento. Supuesto con referencias públicas; validar en entrevista.'
FROM pork_silver.source s WHERE s.name = 'retail_offal_ec_2026';

-- Los 24 escenarios pasan de la v1 a la v2 (mismo valor: base)
UPDATE pork_silver.scenario_assumption sa
JOIN pork_silver.assumption a_old ON a_old.assumption_id = sa.assumption_id
                                  AND a_old.name = 'offal_local_value_usd_kg' AND a_old.version = 1
JOIN pork_silver.assumption a_new ON a_new.name = 'offal_local_value_usd_kg' AND a_new.version = 2
SET sa.assumption_id = a_new.assumption_id;
