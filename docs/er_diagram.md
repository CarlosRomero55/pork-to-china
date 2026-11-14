# Modelo de datos (ER)

Tres bases MySQL: `pork_bronze` (crudo), `pork_silver` (3FN) y `pork_gold` (estrella). Scripts en `sql/`.

## Bronze · crudo inmutable
```mermaid
erDiagram
  extract_batch ||--o{ raw_api_response : genera
  extract_batch ||--o{ raw_file : genera
  raw_file ||--o{ raw_pdf_table : contiene
  extract_batch { BIGINT batch_id PK
    VARCHAR source_name
    ENUM status
    JSON params }
  raw_api_response { BIGINT raw_id PK
    BIGINT batch_id FK
    JSON payload
    CHAR64 payload_hash UK }
  raw_file { BIGINT file_id PK
    BIGINT batch_id FK
    VARCHAR stored_path
    CHAR64 file_hash UK }
  raw_pdf_table { BIGINT row_id PK
    BIGINT file_id FK
    JSON row_values }
```

## Silver · 3FN
```mermaid
erDiagram
  country ||--o{ country_group_member : pertenece
  country_group ||--o{ country_group_member : agrupa
  country ||--o{ trade_flow : "reporter / partner"
  hs_product ||--o{ trade_flow : producto
  source ||--o{ trade_flow : origen
  country ||--o{ trade_measure : "impone / afecta"
  country_group ||--o{ trade_measure : "afecta (bloque)"
  hs_product ||--o{ trade_measure : linea
  source ||--o{ assumption : respaldo
  scenario ||--o{ scenario_assumption : usa
  assumption ||--o{ scenario_assumption : en
  province ||--o{ canton : tiene
  canton ||--o{ sanitary_case : reporta
  country { SMALLINT country_id PK
    CHAR3 iso3 UK
    SMALLINT comtrade_code UK }
  country_group_member { SMALLINT group_id PK
    SMALLINT country_id PK
    DATE valid_from PK
    DATE valid_to }
  hs_product { CHAR6 hs_code PK
    ENUM product_group
    ENUM preservation
    BOOL is_ecuador_supply }
  trade_flow { BIGINT flow_id PK
    DATE period
    ENUM flow_type
    DECIMAL net_weight_kg
    DECIMAL value_usd
    BIGINT batch_id }
  trade_measure { INT measure_id PK
    SMALLINT target_id FK
    SMALLINT target_group_id FK
    VARCHAR target_company
    ENUM measure_type
    DECIMAL rate_pct
    DATE valid_from
    DATE valid_to }
  assumption { INT assumption_id PK
    VARCHAR name
    SMALLINT version
    DECIMAL value_min
    DECIMAL value_base
    DECIMAL value_max }
  scenario { TINYINT scenario_id PK
    ENUM trade_case
    ENUM china_selfsuff
    TINYINT cert_year }
```

## Gold · estrella
```mermaid
erDiagram
  dim_date ||--o{ fact_china_imports : ""
  dim_country ||--o{ fact_china_imports : partner
  dim_product ||--o{ fact_china_imports : ""
  dim_scenario ||--o{ fact_landed_cost : ""
  dim_country ||--o{ fact_landed_cost : supplier
  dim_product ||--o{ fact_landed_cost : ""
  dim_scenario ||--o{ fact_scenario_cashflow : ""
  dim_scenario ||--|| fact_scenario_result : ""
  dim_scenario ||--o{ fact_monte_carlo : ""
  dim_date ||--o{ fact_sanitary_cases : ""
  dim_province ||--o{ fact_sanitary_cases : ""
```

## Decisiones de diseño
1. **Pertenencia a la UE con vigencia** (`country_group_member`): el Reino Unido salió el 31-01-2020.
2. **`trade_measure` en SCD tipo 2** (ADR-002): destino = país, bloque o todos (NMF); tasa por empresa para el antidumping. La columna generada `target_key` permite una clave única aunque haya NULL. "Vigente" se calcula con la fecha (vista `v_trade_measure_current`), porque el antidumping a la UE tiene fin programado en 2030.
3. **Supuestos versionados + escenarios con tabla puente**: los escenarios viejos siguen siendo reproducibles.
4. **Silver guarda unidades crudas** (kg, USD); gold, las métricas derivadas.
5. **`comtrade_code` separado del ISO**: Comtrade usa códigos propios (Francia = 251).
6. **CHECKs**: periodo = día 1, tasas en 0–1000%, mín ≤ base ≤ máx, fechas coherentes.

## Seguridad
- `pork_etl`: lectura/escritura en las 3 bases (pipeline).
- `pork_bi`: solo `SELECT` en `pork_gold` (app de Streamlit y API).
- Root solo se usa una vez, en `db_setup.py`, y su contraseña no se guarda.
