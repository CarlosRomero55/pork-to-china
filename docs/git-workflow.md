# Flujo de trabajo con Git

Este repositorio usa **GitHub Flow con ramas por paso** y etiquetas por fase.

## Ramas
- `main` — siempre estable: solo recibe fusiones de ramas ya verificadas en el PC de desarrollo
  (el script de la fase corre completo y todas las pruebas pasan).
- Una rama corta por paso, creada desde `main`:

| Prefijo | Uso | Ejemplo |
|---|---|---|
| `feat/` | funcionalidad nueva | `feat/fase-08-orquestacion` |
| `fix/` | corrección de un error | `fix/zip-fecha-fija` |
| `docs/` | solo documentación | `docs/cierre-fase-07` |
| `test/` | solo pruebas | `test/gold-integracion` |
| `refactor/` | cambio interno sin cambiar resultados | `refactor/upsert-chunks` |

## Ciclo de cada paso
1. `git switch -c feat/fase-XX-tema` desde `main` actualizado.
2. Commits pequeños con mensajes en español y prefijo convencional (`feat:`, `fix:`, `docs:`, `test:`).
3. `git push -u origin feat/fase-XX-tema`.
4. Verificación: se corre el script de la fase (`.\gold.ps1`, `.\validate.ps1`...) y `pytest`.
5. Solo si todo pasa: fusión a `main` con `git merge --no-ff` (queda un commit de fusión que
   muestra en el historial qué entró junto) y `git push`.
6. Al cerrar una fase: etiqueta anotada `vMAYOR.FASE.PASO` (p. ej. `v0.7.0` = Fase 7 cerrada).

## Por qué
- `main` nunca queda en un estado roto: lo que no pasa las pruebas se queda en su rama.
- El historial cuenta la historia del proyecto paso por paso (`git log --graph`).
- Las etiquetas permiten volver a cualquier fase: `git switch --detach v0.7.0`.

> Las fases 0–7 se desarrollaron directamente en `main`, antes de adoptar este flujo.
> Se etiquetó `v0.7.0` como punto de partida.
