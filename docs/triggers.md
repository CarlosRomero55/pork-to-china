# Disparadores de la recomendación

Generado por `src/recommendation.py` el 2026-11-17. Regla: se revisa la inversión cuando se cumple **una** condición económica (D1 o D2) **y las dos** de acceso (D3 y D4).

**Decisión hoy: no invertir hoy.** Faltan una condición económica (D1 o D2) y las dos de acceso (D3 y D4).

| | disparador | condición | hoy | estado | dónde se vigila |
|---|---|---|---|---|---|
| D1 | Precio en planta de la víscera | Comprar la víscera en planta a 1,14 USD/kg o menos (VAN = 0 en B-up-6) | 1,38 USD/kg (supuesto v2 con precios SIPA; validar en entrevista) | ⛔ no cumplido | silver.assumption · página 4 (simulador) |
| D2 | Precio FOB de las vísceras en China | FOB de referencia (Chile, 020649) de 1,84 USD/kg o más (VAN = 0 en B-up-6) | 1,47 USD/kg (Chile, 12 meses hasta 09-2026) | ⛔ no cumplido | gold.fact_china_imports · página 2 (precio en destino) |
| D3 | Zona libre de peste porcina clásica | La OMSA reconoce una zona continental de Ecuador libre de PPC | Presente en el territorio continental, con vacunación obligatoria en las 23 provincias (1.346.020 cerdos vacunados a jul-2026, meta 2.060.450). La OMSA solo reconoce como libre la zona insular de Galápagos. | ⛔ no cumplido | silver.sanitary_status · página 5 (mapa sanitario) |
| D4 | Protocolo sanitario con China | Ecuador y la GACC firman el protocolo de carne y subproductos de cerdo | Sin protocolo firmado ni proceso público iniciado con la GACC | ⛔ no cumplido | silver.access_benchmark · páginas 5 y 6 |
| D5 | Fiebre aftosa sin vacunación | La OMSA reconoce a Ecuador libre de fiebre aftosa sin vacunación | Vacunación suspendida en 2026; Ecuador busca el estatus de libre sin vacunación ante la OMSA en 2027. | ⏳ en camino | silver.sanitary_status · página 5 (mapa sanitario) |

## Umbrales por escenario (certificación en el año 6, VAN = 0)

Cada umbral supone el otro supuesto en su valor base (víscera 1,38 o FOB 1,60).

| escenario | víscera máxima en planta (USD/kg) | FOB mínimo (USD/kg) |
|---|---|---|
| C-up-6 | 1,19 | 1,79 |
| C-down-6 | 1,19 | 1,79 |
| B-up-6 (referencia) | 1,14 | 1,84 |
| B-down-6 | 1,19 | 1,79 |
| A-up-6 | 1,08 | 1,91 |
| A-down-6 | 1,15 | 1,84 |
