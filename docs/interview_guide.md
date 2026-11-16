# Guion de entrevista · sector porcino de Ecuador (Fase 13)

**Objetivo:** validar los dos supuestos que más mueven el resultado del modelo de AgroPorc:

1. **El valor local de la víscera de cerdo.** El modelo usa 1,14–**1,38**–2,20 USD/kg (supuesto #41). El proyecto solo
   conviene si ese valor es menor que 1,08–1,25 USD/kg.
2. **El plazo del protocolo sanitario con China.** Los escenarios suponen que se certifica en el año 2, 4 o 6, o que nunca se certifica.

**A quién entrevistar** (una persona basta; mejor si son dos de eslabones distintos):
- jefe comercial de una faenadora o planta tecnificada;
- técnico o directivo de ASPE;
- comerciante mayorista de subproductos en un camal o mercado;
- funcionario de Agrocalidad, de sanidad animal.

**Duración:** 30–40 minutos. **Formato:** semiestructurado. Las respuestas se registran en
`data/qualitative/interview_template.csv`, una fila por respuesta.

**Ética:** al inicio, explicar que es un proyecto académico de portafolio con una empresa ficticia (AgroPorc).
Pedir permiso para tomar notas, no grabar sin consentimiento y no publicar el nombre de la persona ni de su
empresa. Guardar solo el **tipo de actor**: `faenadora`, `gremio`, `comerciante` o `autoridad`.

---

## Bloque A · Valor local de la víscera (prioridad 1)

| # | Pregunta | Qué valida en el modelo |
|---|---|---|
| A1 | ¿Qué partes del cerdo, fuera de la carne, vende su empresa o su mercado? (patas, cuero, orejas, estómago, intestinos, hígado, corazón, cabeza) | Qué mezcla de víscera existe |
| A2 | Para cada una: ¿a cuánto la vende **en planta** o al mayorista, por libra o por kilo? ¿Y cuánto paga el consumidor final? | Base de 1,38 USD/kg y factor planta/mercado de 0,52 |
| A3 | ¿Cuáles de esas partes se venden con facilidad y cuáles se quedan sin vender, se regalan o van a harina o desecho? | Qué víscera vale poco aquí y podría exportarse |
| A4 | ¿Cuántos kilos de víscera comestible salen de un cerdo de unos 100 kg en pie? | Rendimiento por animal (hoy no está en el modelo) |
| A5 | Si una planta tuviera 100 toneladas más de patas al mes, ¿el mercado las absorbería al mismo precio? ¿Cuánto cree que bajaría? | Elasticidad: si 5.000 t al año hunden el precio local, exportar mejora |
| A6 | ¿Cómo cambia el precio de la víscera durante el año (por ejemplo, en Navidad o Año Nuevo)? | Estacionalidad del costo de oportunidad |

## Bloque B · Protocolo sanitario y acceso a China (prioridad 2)

| # | Pregunta | Qué valida en el modelo |
|---|---|---|
| B1 | ¿Sabe si Ecuador ha iniciado conversaciones con China (GACC) para un protocolo de carne o vísceras de cerdo? ¿En qué etapa están? | Año de certificación: 2, 4, 6 o nunca |
| B2 | ¿Cuál es hoy el mayor obstáculo sanitario: la peste porcina clásica (PPC), la trazabilidad o la cantidad de plantas habilitadas? | Mapa sanitario (Paso 13.2) |
| B3 | ¿Qué le exigió Vietnam (u otro mercado nuevo) a Pronaca o a otra exportadora, y cuánto tardó? | Benchmark de plazos (Paso 13.3) |
| B4 | ¿Cuánto cuesta adecuar una planta para auditorías de exportación (inversión y tiempo)? | Inversión: adecuación sanitaria 150–250–400 mil USD y habilitación para China 50–100–200 mil USD (supuestos) |

## Bloque C · Cierre

| # | Pregunta |
|---|---|
| C1 | Si usted fuera AgroPorc, ¿exportaría vísceras a China, a otro mercado o las vendería aquí? ¿Por qué? |
| C2 | ¿Qué dato le parece que estoy pasando por alto? ¿Con quién más debería hablar? |

---

## Cómo se usan las respuestas

- **A2 y A3** reemplazan el supuesto #41 con una **v3** de `offal_local_value_usd_kg` (nueva migración),
  idealmente separada por tipo de víscera.
- **A5** puede convertirse en un supuesto nuevo: la caída del precio local por cada 1.000 t extra.
- **B1** ajusta qué años de certificación son plausibles; **B2 y B3** alimentan los pasos 13.2 y 13.3.
- Toda cifra que venga de la entrevista se marca como fuente **"entrevista (tipo de actor, fecha)"** en
  `docs/assumptions.md`. Es una fuente primaria, pero de una sola persona: se reporta como indicio, no como
  dato oficial.
