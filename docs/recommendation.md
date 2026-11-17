# Recomendación para AgroPorc Ecuador

*Una página. Cifras al 17-nov-2026; la versión viva de los disparadores está en `docs/triggers.md` y en la página 9 del tablero, que se recalculan en cada corrida del pipeline.*

## Decisión: no invertir hoy en exportar vísceras de cerdo a China

La guerra comercial sí abrió un espacio (Estados Unidos perdió participación en las vísceras que compra China), pero hoy AgroPorc no puede aprovecharlo con ganancia ni tiene permiso para entrar. La recomendación no es "nunca": es **esperar, preparar lo barato y revisar la decisión cuando se cumplan los disparadores de abajo**.

## Por qué (tres cifras con fuente)

1. **El negocio pierde dinero en los 24 escenarios.** Con la víscera valorada en 1,38 USD/kg en planta (precios de productor del SIPA/MAG para cuero y patitas, ajustados a planta), el valor actual neto es negativo en todos los escenarios. Para llegar a VAN = 0 en el escenario de referencia hay que comprarla a 1,14 USD/kg o menos, un 17% menos. El Monte Carlo de 10.000 sorteos da una probabilidad de ganar de entre 1% y 11% aun con certificación. *Fuente: modelo del proyecto (`fact_scenario_result`, `fact_mc_summary`); supuesto #41 y #50.*
2. **Ecuador no tiene permiso sanitario para entrar.** La OMSA solo reconoce como libre de peste porcina clásica la zona insular de Galápagos; en el continente se vacuna en las 23 provincias (1.346.020 cerdos vacunados a julio de 2026, de una meta de 2.060.450). Chile, Costa Rica y Brasil entraron a China siendo libres (o con zonas libres) y tardaron unos 7 años desde el protocolo. *Fuente: OMSA, Resolución 26 (2024); Agrocalidad; benchmark de acceso (supuestos #44–#46).*
3. **El precio en China va en la dirección equivocada.** El FOB de referencia (Chile, vísceras 020649) fue 1,47 USD/kg en los 12 meses a septiembre de 2026 (1,60 en 2025); el negocio necesita 1,84, un 26% más. *Fuente: UN Comtrade, datos espejo de las importaciones de China.*

Además, la serie de tiempo interrumpida muestra que la ventana es reversible: en 2018 Estados Unidos perdió 9,6 puntos de participación tras los aranceles, pero recuperó 10,2 puntos en 2020 cuando llegaron las exclusiones (`docs/its.md`).

## Disparadores: cuándo revisar la decisión

Se revisa la inversión cuando se cumple **una** condición económica **y las dos** de acceso. Los umbrales económicos salen del modelo (VAN = 0 en el escenario B-up-6: caso comercial central, autosuficiencia china al alza, certificación en el año 6), no de una opinión.

| | condición | hoy | estado |
|---|---|---|---|
| D1 · economía | Comprar la víscera en planta a ≤ 1,14 USD/kg (rango 1,08–1,19 en los 6 escenarios creíbles) | 1,38 USD/kg | ⛔ no cumplido |
| D2 · economía | FOB de referencia en China ≥ 1,84 USD/kg (rango 1,79–1,91) | 1,47 USD/kg | ⛔ no cumplido |
| D3 · acceso | La OMSA reconoce una zona continental libre de peste porcina clásica | Solo Galápagos | ⛔ no cumplido |
| D4 · acceso | Protocolo sanitario de cerdo Ecuador–China firmado con la GACC | Sin protocolo ni proceso público | ⛔ no cumplido |
| D5 · complementario | Libre de fiebre aftosa sin vacunación (OMSA) | Vacunación suspendida en 2026; meta 2027 | ⏳ en camino |

## Qué hacer mientras tanto (acciones baratas que no comprometen la inversión)

1. **Validar el precio de la víscera en planta** con 2 o 3 camales (guion en `docs/interview_guide.md`). Es el supuesto que más mueve el resultado: si el precio real está cerca de 1,14, D1 se cumple sin tocar nada más.
2. **Acompañar la zonificación sanitaria**, junto con ASPE, en las provincias candidatas (Imbabura, Santo Domingo, Guayas, Carchi): es la condición D3 y nadie la cumplirá por AgroPorc.
3. **Probar mercados que ya reciben producto ecuatoriano**, como el envío piloto a Vietnam de septiembre de 2024 (UN Comtrade), para aprender a exportar congelado sin depender de China.
4. **Correr el pipeline cada trimestre**: la página 9 del tablero cambia sola de color cuando un disparador se cumple.

## Riesgos

El pre-mortem (`docs/premortem.md`) enumera ocho formas en que el proyecto podría fracasar. Las dos más probables y de mayor impacto son justo las que hoy frenan la inversión: que no llegue la zona libre de peste porcina clásica (R1) y que la víscera valga más en Ecuador que en China (R2).

*Este documento es un análisis de portafolio sobre una empresa ficticia con datos públicos; no es asesoría de inversión.*
