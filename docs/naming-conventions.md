# Naming Conventions

This guide defines the mandatory naming rules for mart-forge projects. Every model, column, and file must follow these conventions to pass the `mart-review` quality gate.

## Table of Contents

- [Layer Prefixes](#layer-prefixes)
- [Model Naming Patterns](#model-naming-patterns)
- [Window Suffixes](#window-suffixes)
- [Column Naming Rules](#column-naming-rules)
- [File and Directory Layout](#file-and-directory-layout)
- [Examples from Ecommerce Mart](#examples-from-ecommerce-mart)

---

## Layer Prefixes

mart-forge uses a 4-tier Kimball layer architecture plus an Application Data Service (ADS) layer for consumption:

| Layer | Purpose | Materialization |
|-------|---------|-----------------|
| **ODS** | Operational Data Store. Raw data with provenance columns added. Thin 1:1 mapping from source. | `view` or `incremental` |
| **DIM** | Dimension tables. Descriptive context with surrogate keys and SCD handling. | `table` |
| **DWD** | Detail-grain Wide fact tables. Atomically-grained transactions joined to all dimensions via surrogate keys. | `table` or `incremental` |
| **DWS** | Summary/aggregation tables. Pre-computed rollups at coarser grains with time-window semantics. | `table` |
| **ADS** | Application Data Service. One-big-table denormalized views for specific consumers (dashboards, APIs, ML features). | `table` |

Every model name starts with the mart prefix, followed by the layer abbreviation:

```
{prefix}_{layer}_{entity_description}
```

The `prefix` comes from `mart.yml` and is typically a short domain code (3-5 characters).

---

## Model Naming Patterns

### ODS Layer

```
{prefix}_ods_{source}_{entity}
```

- `source` identifies the data provider or raw table being ingested
- `entity` is the business entity name in singular or plural, matching the source

**Rules:**
- One ODS model per source table (1:1 mapping)
- No business logic, joins, or transformations beyond type casting and aliasing
- Must include the 4 provenance columns: `provider`, `pull_ts_utc`, `quote_ts_utc`, `run_id`
- No `SELECT *` -- explicit column list required

**Examples from ecommerce mart:**

| Model Name | Source | Entity |
|---|---|---|
| `ecom_ods_raw_orders` | raw | orders |
| `ecom_ods_raw_customers` | raw | customers |
| `ecom_ods_raw_products` | raw | products |

### DIM Layer

```
{prefix}_dim_{entity}
```

- `entity` is the dimension name in singular form
- Calendar dimensions use `dim_date` by convention
- Role-playing dimensions share the same model (e.g., `dim_date` used as order date and ship date)

**Rules:**
- Must have a surrogate key column: `{entity}_sk` (integer, auto-generated)
- Must have a natural key column: `{entity}_id` (from source)
- Must include an unknown member row with `{entity}_sk = -1`
- SCD Type 2 dimensions must have `effective_from`, `effective_to`, `is_current`

**Examples from ecommerce mart:**

| Model Name | SCD Type | Surrogate Key | Natural Key |
|---|---|---|---|
| `ecom_dim_customer` | Type 2 | `customer_sk` | `customer_id` |
| `ecom_dim_product` | Type 1 | `product_sk` | `product_id` |
| `ecom_dim_date` | Type 0 | `date_key` | `full_date` |

### DWD Layer

```
{prefix}_dwd_{grain_descriptor}_{entity}_di
```

- `grain_descriptor` describes the grain in shorthand (e.g., `order_line`, `trade`, `session`)
- `entity` further qualifies the business process
- `_di` suffix stands for "daily incremental" (the most common pattern)

**Rules:**
- Must declare grain in the `schema.yml` description
- Must join to all relevant dimensions via surrogate keys
- Foreign keys use the dimension's surrogate key name (e.g., `customer_sk`, `product_sk`, `order_date_key`)
- Must have its own surrogate key as primary key
- No `current_timestamp()` in model logic (breaks idempotency)

**Examples from ecommerce mart:**

| Model Name | Grain | Surrogate Key | FK References |
|---|---|---|---|
| `ecom_dwd_order_line_di` | One row per order line item | `order_line_sk` | `customer_sk`, `product_sk`, `order_date_key` |

### DWS Layer

```
{prefix}_dws_{dimension_or_entity}_{metric_group}_{window}
```

- `dimension_or_entity` indicates what axis the aggregation is along
- `metric_group` is the family of measures being rolled up
- `window` is one of the standard window suffixes (see below)

**Rules:**
- Must use a valid window suffix
- Must aggregate from DWD or other DWS models (never directly from ODS)
- Materialized as `table` (full rebuild each run) -- not incremental
- Excluded rows (cancelled, deleted) should be filtered before aggregation

**Examples from ecommerce mart:**

| Model Name | Grain | Window |
|---|---|---|
| `ecom_dws_daily_revenue_1d` | One row per day | `_1d` |
| `ecom_dws_customer_lifetime_td` | One row per current customer | `_td` |
| `ecom_dws_product_trend_nd` | One row per product per day (with rolling windows) | `_nd` |

### ADS Layer

```
{prefix}_ads_{consumer}_{purpose}
```

- `consumer` identifies who or what system consumes this table
- `purpose` describes the use case

**Rules:**
- Wide, denormalized (joins DWS/DWD/DIM into a single flat table)
- Materialized as `table`
- Intended as the final output layer -- downstream tools query this, not upstream layers
- OK to include both detail and summary columns (e.g., daily revenue + MTD revenue)

**Examples from ecommerce mart:**

| Model Name | Consumer | Purpose |
|---|---|---|
| `ecom_ads_executive_dashboard` | executive | dashboard |

---

## Window Suffixes

DWS models use a mandatory window suffix to declare the aggregation window:

| Suffix | Meaning | Description | Example |
|--------|---------|-------------|---------|
| `_1d` | 1-day | Daily snapshot or daily aggregate | `ecom_dws_daily_revenue_1d` |
| `_nd` | N-day rolling | Rolling window (7d, 30d, etc.) computed via window functions | `ecom_dws_product_trend_nd` |
| `_td` | To-date (lifetime) | Cumulative since first occurrence (no time boundary) | `ecom_dws_customer_lifetime_td` |
| `_mtd` | Month-to-date | Cumulative within the current calendar month | *(not used in ecommerce example)* |

### When to Use Each Suffix

- **`_1d`** -- Use when each row represents exactly one calendar day. Good for daily KPI snapshots, daily P&L, daily order counts.
- **`_nd`** -- Use when the model computes rolling windows (e.g., 7-day moving average, 30-day cumulative). The model typically has one row per entity per day, with window function columns.
- **`_td`** -- Use for lifetime/to-date aggregations with no time boundary. Customer LTV, total units ever sold, all-time high. One row per entity.
- **`_mtd`** -- Use for month-to-date running totals that reset each calendar month. Common in financial reporting and budget-vs-actual dashboards.

---

## Column Naming Rules

### General

- All column names use `snake_case` (lowercase, underscores)
- No abbreviations unless universally understood (`id`, `sk`, `ts`, `utc`)
- Boolean columns prefix with `is_` or `has_` (e.g., `is_current`, `is_weekend`, `has_refund`)
- Date columns suffix with `_date` for dates, `_ts` or `_ts_utc` for timestamps

### Surrogate Keys

```
{entity}_sk     -- e.g., customer_sk, product_sk, order_line_sk
```

- Always an integer
- Generated via `row_number()` or equivalent
- `-1` is reserved for the unknown member row

### Natural Keys

```
{entity}_id     -- e.g., customer_id, product_id, order_id
```

- The business identifier from the source system
- Usually a string (varchar) to handle alphanumeric source IDs

### Foreign Keys in Fact Tables

Foreign key columns in DWD/DWS models use the target dimension's surrogate key name:

```
customer_sk     -- FK to dim_customer.customer_sk
product_sk      -- FK to dim_product.product_sk
order_date_key  -- FK to dim_date.date_key (role-playing)
```

### Provenance Columns (ODS only)

Every ODS model must include these 4 columns, always at the end of the SELECT:

| Column | Type | Description |
|--------|------|-------------|
| `provider` | varchar | Source system identifier (e.g., `'csv_seed'`, `'api_v2'`) |
| `pull_ts_utc` | timestamp | When the data was pulled/ingested |
| `quote_ts_utc` | timestamp | When the data was generated at source |
| `run_id` | varchar | Pipeline execution identifier for tracing |

### Measures in DWS/ADS

- Prefix aggregated measures with their aggregation function context:
  - `total_revenue` (sum), `avg_order_value` (average), `order_count` (count distinct)
- Rolling window columns include the window size: `revenue_7d`, `revenue_30d`, `order_count_7d`
- Cumulative columns: `mtd_revenue`, `ytd_revenue`

---

## File and Directory Layout

```
{mart_name}/
+-- models/
|   +-- ods/                      # One file per source table
|   |   +-- {prefix}_ods_*.sql
|   +-- dim/                      # One file per dimension
|   |   +-- {prefix}_dim_*.sql
|   +-- dwd/                      # One file per fact grain
|   |   +-- {prefix}_dwd_*_di.sql
|   +-- dws/                      # One file per aggregation
|   |   +-- {prefix}_dws_*_{window}.sql
|   +-- ads/                      # One file per consumer
|   |   +-- {prefix}_ads_*.sql
|   +-- schema.yml                # All column docs and tests
+-- seeds/                        # CSV reference data
+-- tests/                        # Singular DQC tests
+-- mart.yml                      # Mart configuration
+-- dbt_project.yml               # dbt project config
+-- profiles.yml                  # Connection profiles
+-- dqc_scorecard.json            # DQC pass/fail artifact
```

**Rules:**
- Models are organized into subdirectories by layer
- Each layer subdirectory contains only models of that layer type
- `schema.yml` can be a single file at `models/schema.yml` or split per layer
- Test files follow: `tests/test_dqc_{control_class}.sql`

---

## Examples from Ecommerce Mart

The reference ecommerce mart (`examples/ecommerce-orders-mart/`) demonstrates all conventions:

### Full Model Inventory

| File | Layer | Pattern Applied |
|------|-------|-----------------|
| `ecom_ods_raw_orders.sql` | ODS | `{prefix}_ods_{source}_{entity}` |
| `ecom_ods_raw_customers.sql` | ODS | `{prefix}_ods_{source}_{entity}` |
| `ecom_ods_raw_products.sql` | ODS | `{prefix}_ods_{source}_{entity}` |
| `ecom_dim_date.sql` | DIM | `{prefix}_dim_{entity}` |
| `ecom_dim_customer.sql` | DIM | `{prefix}_dim_{entity}` |
| `ecom_dim_product.sql` | DIM | `{prefix}_dim_{entity}` |
| `ecom_dwd_order_line_di.sql` | DWD | `{prefix}_dwd_{grain}_{entity}_di` |
| `ecom_dws_daily_revenue_1d.sql` | DWS | `{prefix}_dws_{entity}_{metric}_{window}` |
| `ecom_dws_customer_lifetime_td.sql` | DWS | `{prefix}_dws_{entity}_{metric}_{window}` |
| `ecom_dws_product_trend_nd.sql` | DWS | `{prefix}_dws_{entity}_{metric}_{window}` |
| `ecom_ads_executive_dashboard.sql` | ADS | `{prefix}_ads_{consumer}_{purpose}` |

### Naming Checklist for New Marts

- [ ] All model names start with the mart prefix from `mart.yml`
- [ ] ODS models include all 4 provenance columns
- [ ] DIM models have `{entity}_sk` surrogate key and `{entity}_id` natural key
- [ ] DIM models include unknown member row (sk = -1)
- [ ] DWD models end with `_di`
- [ ] DWS models end with a valid window suffix (`_1d`, `_nd`, `_td`, `_mtd`)
- [ ] ADS models follow `{prefix}_ads_{consumer}_{purpose}`
- [ ] All column names are `snake_case`
- [ ] No `SELECT *` in any model
- [ ] Foreign key columns match the target dimension's surrogate key name
