# Methodology

mart-forge follows the Kimball dimensional modeling methodology, adapted for modern data stacks with dbt and DuckDB.

## Four-Tier Data Layer

| Layer | Prefix | Purpose | Materialization |
|---|---|---|---|
| **ODS** | `ods_` | Operational Data Store — raw ingestion, minimal transform | Table |
| **DIM** | `dim_` | Dimensions — conformed, SCD-aware (Type 1, 2, or 3) | Table |
| **DWD** | `dwd_` | Detail facts — atomic grain, immutable business events | Incremental |
| **DWS** | `dws_` | Summary facts — aggregated grain (daily, weekly, lifetime) | Table |
| **ADS** | `ads_` | Application Data Service — one-big-table for BI consumption | Table/View |

## Guides

- [Bus Matrix](docs/bus-matrix.md) — Enterprise bus matrix mapping business processes to dimensions
- [DQC Framework](docs/dqc-framework.md) — Three-tier data quality contract specification
- [Naming Conventions](docs/naming-conventions.md) — Table, column, and model naming standards
- [Agent Orchestration](docs/agent-orchestration.md) — Multi-agent builder/reviewer workflow
- [Provider Abstraction](docs/provider-abstraction.md) — Warehouse-agnostic design with pluggable adapters

## Philosophy

1. **Methodology before code** — Understand the grain, dimensions, and facts before writing SQL
2. **Conformed by default** — Dimensions are shared across marts unless there's a documented reason not to
3. **Auditable grain** — Every fact table declares its grain explicitly; tests enforce it
4. **SCD-aware** — Slowly changing dimensions are a first-class concern, not an afterthought
5. **Documentation as artifact** — The bus matrix, grain declarations, and DQC scorecards are generated alongside the models
6. **Agent-executable** — Every methodology rule is encoded as a template or skill that an AI agent can follow
