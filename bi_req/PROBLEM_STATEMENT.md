# Business Problem Statement

## Why does this framework exist?

Data engineers building dimensional data warehouses face a recurring gap: the Kimball methodology is well-documented (30 years of textbooks and industry practice), but translating it into a working dbt project still requires weeks of manual scaffolding — choosing naming conventions, designing the bus matrix, writing DDL schemas, layering transforms, configuring tests, and documenting lineage.

AI coding agents can generate SQL and dbt models, but they lack structured methodology. Without architectural intent — no grain discipline, no conformed dimensions, no layered test hierarchy — the result is code that passes syntax checks but fails warehouse governance.

Existing tools (AltimateAI, dbt-utils, sqlfluff) optimize **existing** dbt projects through linting, lineage, and validation. They don't help you **design** the warehouse in the first place.

## What problem does mart-forge solve?

mart-forge closes the gap between methodology and execution:

1. **Methodology as code.** Kimball's four-tier architecture (ODS → DIM → DWD → DWS/ADS), bus matrix design, and naming conventions are encoded as templates and validation rules — not just documentation.

2. **Agent-executable specifications.** AI agents can scaffold a production-grade Kimball mart from a `mart.yml` config file, following the same methodology a senior data engineer would apply manually.

3. **Built-in quality gates.** A three-tier Data Quality Contract (DQC) — generic tests, singular business-logic tests, and external reconciliation — ships with every scaffolded mart. Quality is structural, not an afterthought.

4. **Multi-agent orchestration.** A builder agent scaffolds the mart; a reviewer agent audits it against the methodology. Enforceable gates prevent promotion of non-conformant work.

## Who are the target users?

- **Data engineers** bootstrapping a new analytical layer on DuckDB, Snowflake, BigQuery, or Postgres who want Kimball discipline without weeks of manual setup.
- **Solo practitioners** who need enterprise-grade warehouse design without an enterprise team.
- **AI agent builders** who want structured methodology their agents can follow — not just SQL generation, but architectural scaffolding.
- **dbt practitioners** who want opinionated project scaffolding beyond `dbt init`, with dimensional modeling guidance baked in.

## What mart-forge is NOT

- A replacement for dbt — it uses dbt as the transform engine.
- A hosted SaaS product or web UI.
- A real-time streaming solution (batch/daily grain in v1).
- A generic SQL linter (use dedicated tools for that).
- Domain-specific — the framework is warehouse-agnostic in methodology, with dbt-duckdb as the reference implementation.
