# PROGRESO · Pork to China (Ecuador)

## Estado actual
- **Capa:** 1 (MVP publicable)
- **Fase:** 4.3 – Fuentes complementarias
- **Paso:** 4.3a (USDA PSD → bronze) listo → Carlos corre `.\psd.ps1`
- **Repositorio:** https://github.com/CarlosRomero55/pork-to-china (rama main). Commits a nombre de Carlos Romero, sin coautor; Claude los sube desde su entorno.
- **Modo de ejecución:** "un comando por fase": Claude escribe y prueba todo el código en su entorno (Python 3.12) y lo copia a `D:\pork-to-china`; Carlos solo ejecuta un script por fase y pega la salida. (El entorno de Claude no llega a Comtrade/USDA/FAO, así que la extracción corre en el PC de Carlos.)

## Perfil y ritmo (modo mentor)
- SQL y Python: intermedio en ambos
- Finanzas (VAN/TIR): conoce los conceptos, nunca armó un modelo completo → explicar con números del proyecto
- Dedicación: más de 15 h/semana (ritmo intensivo)
- Python 3.14.4 en el PC (Windows); MySQL 8 instalado
- Quiere que Claude haga todo el trabajo
- Pendiente de respuesta: entrevistas con gente del sector, licencia de Power BI, RAM, idioma del README (por ahora: inglés + resumen en español)

## Bitácora (una línea por paso)
- 2026-11-13 · 0.1 · Verificadas las cifras del contexto con fuente y fecha → `docs/assumptions.md`
- 2026-11-13 · 0.2 · Definidos 13 KPIs con fórmula, grano y tabla gold → `docs/kpis.md`
- 2026-11-13 · 0.3 · Arquitectura Medallion: comparativa, diagrama Mermaid y recorrido de un dato → `docs/architecture.md`
- 2026-11-13 · 0.4 · Creados PROGRESO.md, docs y ADR-001, ADR-002, ADR-006
- 2026-11-13 · 1.1 · Estructura de carpetas, .gitignore, .env.example, requirements.txt (19 librerías fijadas), src/config.py, setup.ps1, README borrador
- 2026-11-13 · 1.2 · setup.ps1 OK en el PC (Py 3.14.4); faltaba DB_USER/DB_PASSWORD (los llena db_setup)
- 2026-11-13 · 2.1 · Diagrama ER aprobado (bronze genérico, silver 3FN, gold estrella + fact_scenario_result) → docs/er_diagram.md
- 2026-11-13 · 4.2 · Primera extracción real OK: 4.999 registros. China 2018–2024 completo (12/12 meses); top proveedores ESP, FRA, USA, CHL, CAN (Chile en top 4 → competidor directo y benchmark). Ecuador: solo 2024-09 a Vietnam (= envío piloto de Pronaca, valida los datos); Costa de Marfil 2023 no aparece (revisar HS 1602 en Fase 5). HUECO: China 2025–2026 = 0 registros en Comtrade
- 2026-11-15 · 4.3a-d · Descarga masiva dio HTTP 406 (los archivos existen; el servidor rechaza el encabezado Accept: application/zip). Ahora prueba Accept: */* y, si sigue el 406, identificación de navegador; valida firma ZIP. 61/61 pytest
- 2026-11-15 · 4.3a-c · Diagnóstico en el PC: sin llave 403 (la puerta revisa la llave), llave como parámetro 403, llave en encabezado 500 en TODAS las rutas → llave válida, falla interna de USDA. Plan B automático: verificación rápida de la API (1 llamada) y, si falla, descarga masiva de PSD Online (psd_livestock_csv.zip → bronze.raw_file), filtra 'Meat, Swine'. 59/59 pytest
- 2026-11-15 · 4.3a-b · Primera corrida real: HTTP 500 persistente en el catálogo commodities de USDA (domingo; posible caída o cambio). Se agregó modo diagnóstico (--probe, llave enmascarada) y catálogos opcionales. 55/55 pytest
- 2026-11-15 · 4.3a · extract_psd.py: API oficial apps.fas.usda.gov/OpenData (encabezado API_KEY); código del cerdo buscado en el catálogo; 24 consultas (4 catálogos + 10 años × país/mundo, 2018–2027); solo bronze + reporte de descubrimiento para diseñar silver con la estructura real. 53/53 pytest
- 2026-11-15 · 6.2 · validate.ps1 OK en el PC: 280 filas marcadas, 10 OK · 1 alerta (R08) · 0 errores, 48/48 pytest; reporte regenerado en docs/
- 2026-11-15 · 6.1b · Bug en el PC: UnicodeEncodeError (cp1252) al canalizar la salida de Python con | Select-String. Corrección doble: src/__init__.py fuerza UTF-8 en stdout/stderr y los 6 .ps1 fijan PYTHONUTF8=1 y la codificación de consola. Reproducido y verificado con PYTHONIOENCODING=cp1252
- 2026-11-15 · 6.1 · Migración 002 (quality_flag SET en silver.trade_flow); clean.py combina outlier estadístico (IQR-log por HS×año) + rango plausible de negocio (carne 0,5–15, vísceras 0,3–10, procesado 0,5–100 USD/kg); validate.py con 11 reglas (R01–R11) y reporte automático docs/data_quality_report.md. Con datos reales: 10 OK, 1 alerta (R08: picos 2020–2021 = peste porcina africana, reales), 0 errores. Marcas: 152 atípicos, 5 sin peso, 128 con peso estimado por la fuente. Hallazgo: España HS 020312 en 2018 a 0,27–0,48 USD/kg = probable error de clasificación del exportador. 48/48 pytest
- 2026-11-13 · 5.1b · transform.ps1 OK en el PC: migración 001 aplicada, 11.066 filas en silver, reporte idéntico al del entorno de pruebas, 37/37 pytest
- 2026-11-13 · 5.1 · clean.py (parseo, solo totales, peso 0 → NULL, outliers USD/kg por IQR-log en HS×año), harmonize.py (última versión de bronze → silver.trade_flow; fuentes comtrade / comtrade_mirror; cuarentena de países desconocidos), migrate.py + migración 001 (25% de China al cerdo de Canadá). Probado con los 27 JSON reales del PC: 11.066 filas, 0 cuarentena, 120 outliers marcados, idempotente. Conciliación 2018–2024: peso 0,992 · valor 1,037. Vista previa 2024→2025 (espejo, t): EE. UU. −26,7%, Canadá −28,6%, Brasil −33,8%, España −5,4%, Dinamarca +1,8%, Reino Unido +13,0%. Bug evitado: "Out of sort memory" al ordenar JSON grandes → lectura en 2 pasos. 37/37 pytest
- 2026-11-13 · 4.2c · Corrida real con espejo: MIRROR 2018–2025 completos (12/12) y 2026 hasta septiembre (9/12); 6.067 registros espejo, 11.066 en total en bronze. getDa confirma: China publicó en Comtrade solo hasta 2024-12 (el hueco es de la fuente, no nuestro); Ecuador hasta 2026-03, pero sin exportaciones de cerdo en 2025–2026; 2025 de Ecuador no figura en getDa (verificar). Reintento ante 429 funcionó en real. Incidente: copias al PC en paralelo dejaron archivos viejos; corregido y verificado (30/30 archivos idénticos al repo)
- 2026-11-13 · 4.2b · Extracción espejo (12 exportadores → China, flujo X, 1 consulta por año para todos) + consulta getDa de disponibilidad; 23/23 pytest
- 2026-11-13 · 4.1 · src/extract_comtrade.py: CHN importaciones + ECU exportaciones, mensual 2018→hoy, 12 HS, todos los socios, solo totales (partner2/customs/mot = 0); 18 consultas por corrida completa (cupo gratuito 500/día); caché en data/raw/comtrade con ventana de revisión de 2 años; reintentos exponenciales ante 429/5xx; 401/403 falla sin reintentar. 8 pruebas con API simulada (21/21 en total)
- 2026-11-13 · 3.2 · (pendiente confirmar salida de db_check.ps1 en el PC)
- 2026-11-13 · 3.1 · src/db.py (engine etl/bi, track_batch, save_raw_response con hash, upsert_df idempotente, last_period), src/logging_setup.py (consola + logs/pipeline.log rotativo), tests/test_db.py; 13/13 pytest. Bug detectado por la autoprueba: CLIENT_FOUND_ROWS cuenta 1 en filas sin cambios → fórmula corregida
- 2026-11-13 · 2.3 · db_setup.ps1 OK en el PC de Carlos (usa root del .env una vez, genera contraseñas de pork_etl/pork_bi y saca root del .env). Primer push a GitHub: 4 commits por fase
- 2026-11-13 · 2.2b · db_setup corregido: acepta root sin contraseña, valida root antes de pedir las contraseñas nuevas (3 intentos)
- 2026-11-13 · 2.2 · SQL 01_bronze/02_silver/03_gold + seed + src/db_setup.py + tests/test_schema.py; probado en MySQL 8.0.46: 29 tablas/vistas, 90 medidas SCD2 sin solapes, arancel EE. UU. reconstruido 37/172/57/47%, 6/6 pytest, idempotente
- 2026-11-13 · 1.1b · Corrección: el PC tiene Py 3.14 → pandas 2.2.3 no tenía wheel y pip intentaba compilar. Se actualizaron las versiones (pandas 2.3.3, etc.), verificadas con wheels para Windows en Py 3.12 y 3.14; setup.ps1 ahora se detiene ante errores y usa --only-binary

## Decisiones tomadas
| Fecha | Decisión | ADR |
|---|---|---|
| 2026-11-13 | Carpeta raíz `D:\pork-to-china`; repo en GitHub `CarlosRomero55/pork-to-china` | — |
| 2026-11-13 | Periodo de análisis: 2018 a la fecha | — |
| 2026-11-13 | Granularidad mensual | — |
| 2026-11-13 | Ventana de comparación: 12 meses antes / 12 meses después de cada corte | — |
| 2026-11-13 | Tasa de descuento como supuesto: 10% / 12% / 15% | ADR-003 (pendiente) |
| 2026-11-13 | Horizonte financiero: 10 años | — |
| 2026-11-13 | Arquitectura Medallion en MySQL (silver 3FN tipo Inmon + gold estrella Kimball) | ADR-001 |
| 2026-11-13 | SCD tipo 2 para las medidas comerciales | ADR-002 |
| 2026-11-13 | Empresa ficticia "AgroPorc Ecuador" modelada con datos públicos | ADR-006 |
| 2026-11-13 | venv en .venv; versiones fijadas; .env solo en el PC de Carlos | — |
| 2026-11-13 | 3 bases separadas (pork_bronze/silver/gold), utf8mb4, InnoDB, periodo = día 1 del mes | ADR-001 |
| 2026-11-13 | Usuarios pork_etl (3 capas) y pork_bi (solo gold); root solo en db_setup | — |
| 2026-11-13 | SAM = solo congelados (020322, 020329, 020641, 020649) | — |
| 2026-11-13 | Visualización y simulador What-If en **Streamlit** (en lugar de Power BI); Power BI queda como opción complementaria | ADR-007 |
| 2026-11-13 | Upsert con INSERT … ON DUPLICATE KEY UPDATE (no pandas.to_sql); el registro del lote usa transacciones propias para que un fallo quede auditado | — |
| 2026-11-13 | Comtrade primero; todos los socios; doble caché (bronze + data/raw); ventana de revisión de 2 años | — |
| 2026-11-13 | Llaves de Comtrade y USDA FAS (api.data.gov) obtenidas por Carlos; viven solo en su .env | — |
| 2026-11-13 | Datos espejo (mirror) para cubrir 2025–2026; fuente separada en silver; factor de conciliación medido | ADR-008 |
| 2026-11-13 | Corte vertical: Comtrade a silver antes de extraer otras fuentes | — |
| 2026-11-13 | Cambios de esquema con migraciones versionadas (sql/migrations + schema_migration) | — |
| 2026-11-13 | Canadá es proveedor sancionado (25% desde 20-mar-2025) → nuevo corte de análisis | — |
| 2026-11-15 | Filas dudosas se marcan (quality_flag), no se borran; gold las excluye del precio promedio pero no del volumen | — |
| 2026-11-15 | Atípico = estadístico (IQR) O fuera de rango de negocio | — |
| 2026-11-13 | Cortes de análisis: mar-2025 (EE. UU.), sep-2025 (UE, provisional), dic-2025 (UE, definitivo) | — |

## Hallazgos clave de la Fase 0
- La ventana está en las **vísceras**, no en los cortes: en el 1S-2026 la carne importada por China cayó 26,4% y las vísceras solo 4,8%.
- La tregua EE. UU.–China (hasta el 10-ene-2027) y el posible recorte de aranceles a proteínas de EE. UU. empujan hacia el **escenario A** (la ventana se cierra).
- La Sección 301 vence a fines de 2026: +30 pp posibles al cerdo de EE. UU. (escenario C).
- Ecuador sigue vacunando contra la PPC (no es libre). Suspendió la vacunación contra la aftosa en marzo de 2026 y apunta a un nuevo estatus en 2027.
- ASPE: el maíz encarece los costos de producción entre 30% y 40% frente a otros mercados → riesgo para el landed cost.

## Pendientes
- [ ] Confirmar en la lista oficial de la OMSA que Ecuador no tiene ninguna zona libre de PPC
- [ ] Obtener la canasta de desgravación de las partidas HS 0203, 0206 y 0210 en el acuerdo Ecuador–China (texto oficial del MPCEIP)
- [ ] Confirmar si existe un protocolo sanitario de cerdo Ecuador–China (no se encontró ninguno firmado)
- [x] Discrepancia del arancel a EE. UU. resuelta: 57% fue may–nov 2025; vigente 47%
- [ ] Verificar NMF de China por línea HS en WTO TDF (sembrado 12% para 0203/0206)
- [ ] Tasas antidumping por empresa (lista MOFCOM) → hoy solo mín/máx de muestreadas
- [ ] Respuestas pendientes de Carlos (entrevistas, Power BI, RAM, idioma del README)
- [ ] Preguntas de entrevista de cierre de la Fase 0 (opcionales)
- [ ] ADR-003, ADR-004 y ADR-005
- [ ] Verificar por qué Ecuador 2025 no figura en getDa y si el envío a Costa de Marfil 2023 salió por HS 1602
- [ ] Costa Rica exporta cerdo a China → agregar al benchmark sanitario (Fase 13)

## Siguiente paso
**Paso 4.3a:** Carlos corre `.\psd.ps1` (usará la descarga masiva si la API sigue caída) y pega el reporte de descubrimiento. Luego: 4.3b silver de PSD (migración 003 + regla de balance oferta = demanda), FAOSTAT y aranceles NMF por línea HS; después Fase 7 (gold).
