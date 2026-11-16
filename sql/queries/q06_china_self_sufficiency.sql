-- Pregunta: ¿Se está cerrando la ventana de importación de China? Autosuficiencia e importaciones 2018–2027.
-- Técnica: LAG() para variación en puntos + AVG() OVER (ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) (media móvil 3 años)
--          + FIRST_VALUE() para comparar contra el pico de la crisis de PPA
-- Fuente: pork_gold.fact_market_balance (USDA PSD, miles de t CWE)
-- Lectura: las importaciones de 2027 (proyección) son el 15,5% del pico de 2020; la autosuficiencia pasa de
--          87,5% a 99,0%. La ventana de la PPA se cerró: el mercado para recién llegados es un nicho.
SELECT market_year                                                    AS año,
       ROUND(production_kt)                                           AS produccion_kt,
       ROUND(imports_kt)                                              AS importa_kt,
       self_sufficiency_pct                                           AS autosuf_pct,
       ROUND(self_sufficiency_pct - LAG(self_sufficiency_pct) OVER w, 2) AS cambio_pp,
       ROUND(AVG(imports_kt) OVER (w ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)) AS importa_media3,
       ROUND(100 * imports_kt / MAX(imports_kt) OVER (), 1)          AS pct_del_pico,
       IF(is_projection, 'proyección', 'cerrado')                     AS estado
FROM pork_gold.fact_market_balance
WHERE psd_code = 'CH'
WINDOW w AS (ORDER BY market_year)
ORDER BY market_year;
