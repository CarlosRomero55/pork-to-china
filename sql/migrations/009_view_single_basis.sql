-- =====================================================================
-- 009 · v_supplier_tonnes: serie continua de UNA sola base (espejo)
-- La versión de la 005 unía directo (hasta 2024-12) y espejo (desde 2025-01). Al comparar
-- periodos que cruzan ese corte, el cambio de fuente se confundía con un cambio de mercado
-- (EE. UU. salía +20% en carne cuando en realidad cayó 33%). El espejo cubre 2018–2026
-- completo para los 12 exportadores: es la base correcta para series de tiempo.
-- =====================================================================
CREATE OR REPLACE VIEW pork_gold.v_supplier_tonnes AS
SELECT f.date_key, f.partner_key, f.product_key, f.tonnes, f.basis
FROM pork_gold.fact_china_imports f
WHERE f.basis = 'mirror';
