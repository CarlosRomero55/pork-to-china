# API de Pork to China

FastAPI de solo lectura sobre `pork_gold` (usuario `pork_bi`) + un simulador What-If que recalcula en memoria
con las mismas funciones del pipeline (`src/finance.py`). Levantarla: `.\api.ps1` → <http://127.0.0.1:8000/docs>.

| Método | Ruta | Devuelve |
|---|---|---|
| GET | `/health` | Estado de la API y de la base, y última corrida del pipeline |
| GET | `/scenarios` | Los 24 escenarios con VAN, TIR, payback, equilibrio, divisas y empleos (ordenados por VAN) |
| GET | `/scenarios/{code}` | Un escenario: resultado, mercado año a año y flujo de caja (años 0–10) |
| GET | `/tariffs?origin=ECU&hs=020649&month=AAAA-MM` | Arancel efectivo de China y sus componentes |
| GET | `/landed-cost?scenario=B-up-2&hs=020649` | Costo puesto en China por proveedor, ordenado |
| GET | `/market/china-balance` | Balance de cerdo de China (USDA, miles de t CWE), 2018–2027 |
| POST | `/simulate` | VAN, TIR y payback moviendo tasa, valor de la víscera, FOB, capacidad e inversión |

## Ejemplo de simulación

```json
POST /simulate
{"scenario": "B-up-4", "offal_local_value_usd_kg": 1.2}
```

Respuesta (resumida): `npv_usd ≈ −3.170`, `delta_npv_usd ≈ −1.881.805` → con la víscera a 1,20 USD/kg el
escenario B-up-4 queda en su punto de equilibrio.

## Decisiones
- **Mínimo privilegio:** `pork_bi` solo lee `pork_gold`. Lo que la API necesita de silver (supuestos) y de bronze
  (última corrida) se expone con dos vistas en gold (`v_scenario_params`, `v_last_pipeline_run`, migración 014),
  sin dar permisos sobre esas capas.
- **Un solo lugar para el cálculo:** `/simulate` usa `finance.evaluate()`; sin cambios reproduce el VAN del pipeline
  (prueba automática).
- **Validación en la entrada:** Pydantic y patrones en los parámetros (HS de 6 dígitos, ISO3, AAAA-MM, rangos de la
  simulación) → 422 antes de tocar la base; recursos inexistentes → 404.
