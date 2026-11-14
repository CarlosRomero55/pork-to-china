# ADR-006 · Empresa ficticia modelada con datos públicos

- **Estado:** Aceptada
- **Fecha:** 2026-11-13

## Contexto
Un estudio de entrada a mercado necesita un "cliente" con preguntas concretas (invertir o no en certificación, a qué escala). No existe acceso a datos internos de ninguna empresa porcícola ecuatoriana, y usarlos o inventarlos sería poco ético y poco creíble.

## Decisión
El caso se plantea para **"AgroPorc Ecuador"**, una empresa ficticia cuyos parámetros (escala, costos, inversión) se construyen solo con datos públicos de la industria (ASPE, MAG, Aprobal, FAOSTAT, prensa especializada) y con supuestos documentados en rangos mín/base/máx.
- Pronaca aparece únicamente como referencia pública (por ejemplo, sus exportaciones piloto a Costa de Marfil y Vietnam).
- Nunca se usan ni se inventan datos internos de ninguna empresa.

## Alternativas consideradas
- Analizar una empresa real: no hay datos y habría riesgo reputacional y legal.
- Un análisis solo a nivel país: pierde el ángulo de decisión de negocio (VAN, TIR, equilibrio).

## Consecuencias
- (+) Se puede mostrar un modelo financiero completo sin comprometer a nadie.
- (+) Cada supuesto es trazable en `silver.assumptions`.
- (−) Los resultados son indicativos, no una valoración de una empresa concreta; se declara en el README.
