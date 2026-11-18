# Posts de LinkedIn · Pork to China

Borradores para publicar desde la cuenta de Carlos. Todas las cifras salen del proyecto (corrida 86, 17-nov-2026).
Orden sugerido: post principal → seguimiento 1 a los 3–4 días → seguimiento 2 → seguimiento 3. Un post por semana mantiene el tema vivo sin cansar.

---

## Post principal · la historia completa

**Imagen:** `docs/img/dashboard_9_recomendacion.png` (o el gráfico `docs/img/brief_margin.png`)

> ¿Puede Ecuador aprovechar la guerra comercial entre EE. UU. y China para venderle cerdo?
>
> Me hice esa pregunta y la respondí con datos públicos, como si fuera el analista de una empresa porcina ecuatoriana (ficticia: AgroPorc Ecuador).
>
> Lo que encontré:
>
> 🔹 La ventana existe. Tras los aranceles de 2025, EE. UU. bajó de 28,7% a 22,8% de las vísceras de cerdo que compra China.
> 🔹 Pero se cierra. En 2018 EE. UU. perdió 9,6 puntos y en 2020 recuperó 10,2 cuando llegaron las exclusiones.
> 🔹 Ecuador no tiene permiso sanitario. La OMSA solo reconoce a Galápagos como libre de peste porcina clásica. Chile, Costa Rica y Brasil entraron siendo libres y tardaron unos 7 años.
> 🔹 Y aun con permiso, hoy cada kilo exportado dejaría −0,16 USD de margen. El VAN es negativo en los 24 escenarios que modelé.
>
> Mi recomendación: no invertir hoy. Pero no "nunca": definí 5 disparadores medibles (precio de la víscera, precio en China, zona libre, protocolo con China) que, si se cumplen, reabren la decisión. El tablero los recalcula solo en cada corrida.
>
> Cómo lo construí:
> • Almacén MySQL en capas (bronze → silver → gold) con UN Comtrade, USDA, INEC y fuentes sanitarias
> • Pipeline en Python de 15 etapas con 210 pruebas automáticas
> • Modelo financiero, serie de tiempo interrumpida y Monte Carlo de 10.000 sorteos
> • Tablero de 9 páginas en Streamlit, API en FastAPI y un policy brief de 2 páginas
>
> El repositorio, con el código y la documentación: github.com/CarlosRomero55/pork-to-china
>
> ¿Qué otra industria ecuatoriana podría aprovechar (o no) este tipo de ventanas?
>
> #DataAnalytics #DataEngineering #Python #SQL #ComercioExterior #Ecuador #China

---

## Seguimiento 1 · "¿Y si vendemos más volumen?"

**Imagen:** `docs/img/brief_margin.png`

> "China compra más de un millón de toneladas de vísceras de cerdo al año. ¿Por qué no venderle más volumen?"
>
> Fue la primera objeción que me hice en el proyecto Pork to China, y la respuesta me sorprendió.
>
> El cálculo por kilo, hoy:
> China paga 1,47 USD
> − la víscera vale 1,38 en Ecuador (lo que dejas de ganar al no venderla aquí)
> − proceso, congelado y logística: 0,25
> = −0,16 USD por kilo
>
> Con margen negativo, más volumen es más pérdida. En el modelo, pasar de 5.000 a 50.000 toneladas al año empeora el VAN, no lo mejora.
>
> El volumen multiplica ganancias solo cuando cada kilo deja algo. Por eso la pregunta útil no es "¿cuánto compra China?", sino "¿cuánto deja cada kilo?".
>
> Y como Ecuador está dolarizado y China paga en dólares, tampoco hay ganancia por tipo de cambio.
>
> Proyecto completo: github.com/CarlosRomero55/pork-to-china
>
> #DataAnalytics #Finanzas #ComercioExterior #Ecuador

---

## Seguimiento 2 · la ventana que se abre y se cierra

**Imagen:** `docs/img/brief_us_share.png`

> ¿Las guerras comerciales cambian de verdad quién le vende a China, o solo por un rato?
>
> Medí el efecto con una serie de tiempo interrumpida: 11 años de importaciones mensuales de vísceras de cerdo de China, con cortes en los aranceles de 2018 y en las exclusiones de 2020.
>
> Resultado:
> 📉 2018: EE. UU. pierde 9,6 puntos de participación (p = 0,02)
> 📈 2020: recupera 10,2 puntos (p = 0,001) cuando China empieza a dar exclusiones
>
> Lección para cualquier exportador: una ventana abierta por aranceles puede cerrarse con una firma. Construir una planta para aprovecharla toma años; la tregua puede llegar en meses.
>
> Detalle técnico: regresión segmentada con efectos de mes y errores de Newey-West, implementada en NumPy y verificada con datos sintéticos.
>
> github.com/CarlosRomero55/pork-to-china
>
> #DataScience #Econometría #ComercioExterior #Python

---

## Seguimiento 3 · para reclutadores técnicos (data engineering)

**Imagen:** captura del diagrama de arquitectura del README o de la salida de `.\pipeline.ps1`

> Lo que no se ve en un tablero: cómo está construido por dentro.
>
> En Pork to China quise que el análisis se pudiera repetir de punta a punta con un solo comando:
>
> ✅ Arquitectura Medallion en MySQL: bronze crudo e inmutable, silver normalizado, gold en esquema estrella
> ✅ Migraciones versionadas con checksum: una migración aplicada nunca se edita
> ✅ Aranceles con historia (SCD tipo 2): puedo reconstruir el arancel de cualquier mes
> ✅ Mínimo privilegio: el tablero y la API solo leen gold
> ✅ 15 etapas en subprocesos aislados, con bitácora de cada corrida y candado contra corridas simultáneas
> ✅ 210 pruebas automáticas, incluida una que verifica que las cifras del README coinciden con la base
>
> Si el modelo cambia, el tablero, el policy brief y hasta el README se enteran.
>
> github.com/CarlosRomero55/pork-to-china
>
> #DataEngineering #SQL #Python #MySQL #ETL
