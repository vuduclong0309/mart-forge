# Naming Conventions

## Data Layer Prefixes

| Layer | Prefix | Purpose | Materialization |
|---|---|---|---|
| ODS | `ods_` | Operational Data Store — raw ingestion | Table |
| DIM | `dim_` | Dimensions — conformed, SCD-aware | Table |
| DWD | `dwd_` | Detail facts — atomic grain | Incremental |
| DWS | `dws_` | Summary facts — aggregated grain | Table |
| ADS | `ads_` | Application Data Service — one-big-table | Table/View |

## Column Naming

- Surrogate keys: `{table}_sk` (e.g., `customer_sk`)
- Natural keys: `{table}_nk` or domain-specific (e.g., `customer_id`)
- Date columns: `{event}_date` (e.g., `order_date`)
- Timestamps: `{event}_at` (e.g., `created_at`)
- SCD columns: `valid_from`, `valid_to`, `is_current`
- Measures: descriptive name with unit if ambiguous (e.g., `revenue_usd`, `quantity`)
