# Provider Abstraction

<!-- Warehouse-agnostic methodology with pluggable adapters. -->

## Design Principle

The methodology (Kimball 4-tier layers, naming conventions, DQC framework) is warehouse-agnostic. The reference implementation uses **dbt-duckdb**, but the templates are designed to work with any dbt adapter.

## v1 Reference Implementation

- **Transform engine:** dbt-core
- **Warehouse adapter:** dbt-duckdb
- **Local warehouse:** DuckDB
- **Cloud warehouse:** MotherDuck (deferred until volume justifies)

## Future Adapters

Templates use standard SQL and dbt Jinja macros. Adapter-specific SQL (e.g., `QUALIFY`, `MERGE`) is isolated in macros for easy porting to Snowflake, BigQuery, or Postgres.
