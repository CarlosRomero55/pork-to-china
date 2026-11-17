# Pre-mortem de AgroPorc

Ejercicio: *es 2032, AgroPorc invirtió en exportar vísceras a China y fracasó. ¿Por qué?* Generado por `src/recommendation.py`. **La probabilidad y el impacto son juicio del analista**, no salen de un modelo; la señal temprana y el lugar donde se vigila sí salen de los datos del proyecto.

| | causa del fracaso | probabilidad | impacto | disparador | señal temprana | dónde se vigila |
|---|---|---|---|---|---|---|
| R1 | Nunca llega la zona libre de peste porcina clásica (o llega después de 2032) | alta | alto | D3 | Vacunación por debajo de la meta (1.346.020 de 2.060.450 cerdos a jul-2026); brotes nuevos en provincias candidatas | silver.sanitary_status · página 5 |
| R2 | La víscera vale más en Ecuador que en China: el mercado local la absorbe | alta | alto | D1 | Precio de productor del cuero y las patitas (SIPA) por encima de 1,14 USD/kg en planta | silver.assumption · página 4 |
| R3 | Los precios FOB en China siguen bajando por sobreoferta de los grandes proveedores | media | alto | D2 | FOB de Chile en 020649 bajo 1,50 USD/kg en 12 meses (hoy 1,47; 1,18 en sep-2026) | gold.fact_china_imports · página 2 |
| R4 | Tregua duradera EE. UU.–China: el cerdo de EE. UU. recupera su lugar | media | alto | — | Baja el arancel a las vísceras de EE. UU.; la serie de tiempo ya mostró +10,2 pp para EE. UU. tras las exclusiones de 2020 | gold.fact_tariff_applied · páginas 6 y 7 |
| R5 | El protocolo con la GACC tarda más de 7 años (lo que tardaron Costa Rica y Brasil) | alta | medio | D4 | Sin proceso público iniciado con la GACC a fines de 2027 | silver.access_benchmark · página 5 |
| R6 | AgroPorc no reúne 5.000 t de víscera de camales habilitados para exportar | media | alto | — | Pocas plantas con registro sanitario en las provincias candidatas (Imbabura, Santo Domingo, Guayas, Carchi) | silver.province_pigs · página 5 |
| R7 | Entra la peste porcina africana a Ecuador y se cierran todos los mercados | baja | alto | — | Brotes en países con comercio o vuelos directos (en 2025, casos en España según Agrocalidad) | silver.sanitary_status · página 5 |
| R8 | China produce más y compra menos cerdo importado | media | medio | — | Importaciones chinas de USDA PSD a la baja dos años seguidos | gold.fact_market_balance · página 1 |

## Matriz de riesgo

| impacto \ probabilidad | baja | media | alta |
|---|---|---|---|
| **alto** | R7 | R3, R4, R6 | R1, R2 |
| **medio** | — | R8 | R5 |

Lectura: los dos riesgos de la esquina alta-alta (R1 sanitario y R2 económico) son justo los que hoy frenan la inversión. Por eso la recomendación no es "nunca", sino "no hoy" y vigilar los disparadores.
