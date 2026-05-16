# E-Commerce Orders Mart

Primary example mart for the mart-forge framework. Demonstrates a complete Kimball data warehouse built on synthetic e-commerce order data using dbt + DuckDB.

## Quick Start

```bash
cd examples/ecommerce-orders-mart
pip install dbt-core dbt-duckdb
dbt seed --profiles-dir .
dbt run --profiles-dir .
dbt test --profiles-dir .
```

## Architecture

**Grain:** per-order-line-per-day

### Data Layers

| Layer | Models | Description |
|-------|--------|-------------|
| ODS | `ecom_ods_raw_orders`, `ecom_ods_raw_customers`, `ecom_ods_raw_products` | Raw ingestion from CSV seeds with provenance columns |
| DIM | `ecom_dim_date`, `ecom_dim_customer`, `ecom_dim_product` | Conformed dimensions with surrogate keys and unknown members |
| DWD | `ecom_dwd_order_line_di` | Cleaned fact table with FK resolution to all dimensions |
| DWS | `ecom_dws_daily_revenue_1d`, `ecom_dws_customer_lifetime_td`, `ecom_dws_product_trend_nd` | Aggregations: daily, to-date, and N-day rolling windows |
| ADS | `ecom_ads_executive_dashboard` | One-big-table for executive reporting |

## Bus Matrix

```
                          dim_date   dim_customer   dim_product
dwd_order_line_di            X           X              X
dws_daily_revenue_1d         X
dws_customer_lifetime_td                 X
dws_product_trend_nd         X                          X
ads_executive_dashboard      X           X              X
```

## Dimension Change Strategy

| Dimension | SCD Type | History Columns |
|-----------|----------|-----------------|
| `ecom_dim_date` | Type 0 | N/A (immutable calendar) |
| `ecom_dim_customer` | Type 2 | `effective_from`, `effective_to`, `is_current` |
| `ecom_dim_product` | Type 1 | N/A (overwrite on change) |

All dimensions include an **unknown member** row (SK = -1) for late-arriving or missing FK resolution.

## Synthetic Data

| Seed | Rows | Description |
|------|------|-------------|
| `raw_orders.csv` | 550+ | Order lines across 200+ orders, multiple dates and statuses |
| `raw_customers.csv` | 80 | 60 unique customers; 15 with tier changes (SCD Type 2 demo) |
| `raw_products.csv` | 25 | Products across 5 categories |
| `dim_date.csv` | 731 | Calendar days 2024-01-01 to 2025-12-31 |

## DQC Control Catalog

All 8 control classes implemented:

| Control Class | Implementation | Status |
|---------------|----------------|--------|
| PK Integrity | `not_null` + `unique` on all surrogate keys | pass |
| FK Integrity | `relationships` tests on fact table FKs | pass |
| Freshness | Singular test on `pull_ts_utc` | pass |
| Completeness / Volume | Singular test on minimum row counts | pass |
| Accepted Ranges | `accepted_values` for enums + singular numeric range checks | pass |
| Duplicate Detection | Singular test on `(order_id, line_id)` grain | pass |
| Null-Rate Threshold | Singular test: null rate < 5% on fact columns | pass |
| Business Reconciliation | Singular test: mart totals vs seed CSV totals | pass |

See `dqc_scorecard.json` for the machine-readable scorecard.
