# Tablero en línea (Streamlit Community Cloud)

El tablero corre en tu PC contra MySQL. Para que cualquiera lo abra desde el portafolio, la versión publicada lee
una **copia de gold en Parquet** (`data/snapshot/`) con DuckDB y las **mismas consultas SQL** del tablero.

| | En tu PC (`.\dashboard.ps1`) | En la web (Streamlit Cloud) |
|---|---|---|
| Fuente | MySQL `pork_gold`, usuario `pork_bi` | `data/snapshot/*.parquet` |
| Actualización | Cada `.\pipeline.ps1` | Cada `.\snapshot.ps1` + `git push` |
| Credenciales | `.env` (solo en tu PC) | Ninguna |

El modo se elige solo (`src/gold_source.py`): con `BI_PASSWORD` en el `.env` usa MySQL; sin credenciales y con copia,
usa la copia. Para forzarlo: variable `PORK_DATA=mysql` o `PORK_DATA=snapshot`.

## 1. Exportar la copia (en tu PC, cada vez que corras el pipeline)

```powershell
git pull
.\snapshot.ps1
git add data/snapshot
git commit -m "Copia pública de gold para el tablero en línea"
git push
```

`snapshot.ps1` exporta las 23 tablas y vistas, escribe `manifest.json` (fecha y última corrida) y corre
`tests/test_snapshot.py` con la copia: todas las consultas y las 9 páginas deben cargar sin MySQL.
Solo se exportan datos públicos ya agregados; nunca credenciales ni datos personales.

## 2. Publicar la app (una sola vez)

1. Entra a <https://share.streamlit.io> con tu cuenta de GitHub.
2. **Create app** → **Deploy a public app from GitHub**.
3. Repository: `CarlosRomero55/pork-to-china` · Branch: `main` · Main file path: `src/dashboard/app.py`.
4. App URL: elige un nombre corto, por ejemplo `pork-to-china`.
5. **Advanced settings** → Python version **3.12**. No hace falta ningún secreto.
6. **Deploy**. La primera vez tarda unos minutos en instalar las librerías.

Cada `git push` a `main` actualiza la app sola.

## Límites del plan gratis

- Si nadie la abre en unos días, la app se duerme; la primera visita la despierta en unos segundos.
- Muestra los datos de la última copia exportada, no se actualiza sola desde las APIs.
