# Methodology

mart-forge follows the Kimball dimensional modeling methodology, adapted for modern data stacks with dbt and DuckDB.

## Guides

- [Kimball Fundamentals](docs/methodology/kimball-fundamentals.md) — Dimensional modeling primer
- [Grain Definition](docs/methodology/grain-definition.md) — How to declare and enforce fact table grain
- [Slowly Changing Dimensions](docs/methodology/scd-patterns.md) — SCD Type 1, 2, and 3 implementation patterns
- [Conformed Dimensions](docs/methodology/conformed-dimensions.md) — Building shared dimensions across marts
- [Bus Matrix](docs/methodology/bus-matrix.md) — Enterprise bus matrix design and maintenance
- [Naming Conventions](docs/methodology/naming-conventions.md) — Table, column, and model naming standards
- [Data Quality](docs/methodology/data-quality.md) — Testing strategies for dimensional models

## Philosophy

1. **Methodology before code** — Understand the grain, dimensions, and facts before writing SQL
2. **Conformed by default** — Dimensions are shared across marts unless there's a documented reason not to
3. **Auditable grain** — Every fact table declares its grain explicitly; tests enforce it
4. **SCD-aware** — Slowly changing dimensions are a first-class concern, not an afterthought
5. **Documentation as artifact** — The bus matrix and grain declarations are generated alongside the models
