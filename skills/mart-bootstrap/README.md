# mart-bootstrap

Scaffold a complete Kimball data warehouse mart from a `mart.yml` configuration file.

## What it does

Reads a `mart.yml` and generates:
- Full directory structure (`models/{ods,dim,dwd,dws,ads}/`, `seeds/`, `tests/`)
- All dbt model SQL files following Kimball 4-tier architecture
- `schema.yml` with generic tests implementing all 8 DQC control classes
- Dimension seeds (date calendar, entity reference data) with unknown member rows
- Singular tests for business-logic assertions and reconciliation
- `dqc_scorecard.json` template with all control classes
- GitHub Actions workflow from mart.yml schedule config

## Trigger phrases

- "bootstrap a mart for {domain/source}"
- "scaffold a new mart from mart.yml"
- "create the dbt project for {domain}"

## Prerequisites

- A valid `mart.yml` config file (see `templates/mart.yml.template` for schema)
- dbt-core + dbt-duckdb installed (or target adapter)

## References

- Naming conventions: `docs/naming-conventions.md`
- DQC control catalog: `docs/dqc-framework.md`
- Bus matrix design: `docs/bus-matrix.md`
- Reference implementation: `examples/ecommerce-orders-mart/`
