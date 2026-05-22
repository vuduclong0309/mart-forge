<p align="center">
  <h1 align="center">mart-forge</h1>
  <p align="center">
    Methodology-first Kimball data warehouse scaffolding via AI agents
  </p>
</p>

<p align="center">
  <a href="https://github.com/vuduclong0309/mart-forge/actions"><img src="https://img.shields.io/github/actions/workflow/status/vuduclong0309/mart-forge/gme-mart-ci.yml?branch=main&label=CI" alt="CI Status"></a>
  <a href="https://pypi.org/project/mart-forge/"><img src="https://img.shields.io/pypi/v/mart-forge?color=blue" alt="PyPI Version"></a>
  <a href="https://github.com/vuduclong0309/mart-forge/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-green" alt="License"></a>
  <a href="https://github.com/vuduclong0309/mart-forge/stargazers"><img src="https://img.shields.io/github/stars/vuduclong0309/mart-forge" alt="Stars"></a>
</p>

---

## The Problem

Building a dimensional data warehouse the *right* way — with proper Kimball methodology, conformed dimensions, slowly-changing dimensions, and auditable grain — is hard. Most teams either:

1. **Skip the methodology** and end up with an unmaintainable tangle of one-off SQL
2. **Hire expensive consultants** who leave behind a warehouse nobody understands
3. **Use generic dbt starters** that give you project structure but zero domain modeling guidance

## What mart-forge Does

mart-forge is an **opinionated, methodology-first framework** that pairs Kimball dimensional modeling best practices with AI agents to scaffold production-grade data marts from the ground up.

Given a `mart.yml` config and a data source contract, mart-forge scaffolds a complete Kimball mart — ODS, DIM, DWD, DWS, ADS — with a DQC control catalog, CI pipeline, and machine-readable quality gates.

## Inspired By

mart-forge takes inspiration from [AltimateAI's dbt tooling](https://github.com/AltimateAI/altimate-code), which pioneered the approach of applying AI to data engineering workflows. AltimateAI excels at improving *existing* dbt projects through linting, documentation, lineage, and validation.

mart-forge focuses on a different part of the lifecycle: **designing and scaffolding new warehouses** using Kimball methodology as the knowledge base. Where AltimateAI is tool-focused (make your existing project better), mart-forge is methodology-focused (build a new warehouse the right way from the start). They are complementary — use AltimateAI to lint and document the marts that mart-forge scaffolds.

## Quick Start

### Prerequisites

- Python 3.10+
- [dbt-core](https://docs.getdbt.com/docs/core/installation) with dbt-duckdb adapter
- [Claude Code](https://claude.ai/claude-code) (for AI-assisted scaffolding)

### Installation

```bash
pip install mart-forge
```

### Run the Example Mart

The canonical example mart uses a **fixture-backed data source** (a bundled Parquet snapshot) so it runs offline with no API keys or network access:

```bash
cd examples/gme-options-mart
pip install dbt-core dbt-duckdb
dbt seed --profiles-dir .
dbt run --profiles-dir .
dbt test --profiles-dir .
```

> The fixture is controlled by `use_fixture: true` in `dbt_project.yml`. Set it to `false` to pull live delayed data from CBOE instead (requires network access).

### Build Your Own Mart

mart-forge enforces a methodology-first lifecycle. You cannot scaffold models until the design documents are signed off:

```
[A] BRD → approval → [B] TDD → approval → [C] Scaffold → [D] DQC → [E] Presentation
```

**Phase A — Business Requirements:**

```bash
# 1. Create a mart.yml config for your data domain
#    (see templates/mart.yml.template for the schema)

# 2. Generate the Business Requirements Document (BRD)
claude /mart-brd
```

Review `business-requirements.md`. Set both sign-off lines (operator + consumer) to `approved` before proceeding.

**Phase B — Technical Design:**

```bash
# 3. Generate the Tech Design Document
claude /mart-tdd
```

Review `tech-design-doc.md`. Set both sign-off lines (tech lead + reviewer) to `approved`.

**Phase C — Scaffold:**

```bash
# 4. Generate all dbt models (only runs if both documents are signed off)
claude /mart-bootstrap
```

Or let the framework detect your current phase automatically:

```bash
claude /using-mart-forge
```

### What Gets Generated

The full lifecycle produces these artifacts:

```
my-mart/
├── mart.yml                  # Domain config (you create this)
├── business-requirements.md  # Phase A — BRD with metrics catalog + glossary
├── sign-off-prd.md           # Generated summary (produced alongside TDD, not a Phase A gate)
├── tech-design-doc.md        # Phase B — column-level specs + traceability matrix (must be approved)
├── models/
│   ├── ods/                  # Operational Data Store — explicit column list, provenance columns
│   ├── dim/                  # Dimensions — conformed, SCD-aware, unknown member row (sk=-1)
│   ├── dwd/                  # Detail facts — atomic grain, FK joins via surrogate keys
│   ├── dws/                  # Summary facts — window suffixes (_1d, _nd, _td, _mtd)
│   └── ads/                  # Application Data Service — one-big-table denormalized
├── seeds/
│   └── dim_date.csv          # Reference date dimension
├── tests/                    # Grain enforcement, freshness, completeness, null-rate, ranges
├── dqc_scorecard.json        # Machine-readable quality gate (all 8 DQC control classes)
└── .github/workflows/
    └── daily.yml             # CI/CD + scheduled refresh
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     mart-forge (this repo)                       │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ Methodology  │  │ Mart         │  │ Claude Code Skills     │ │
│  │ Docs         │  │ Templates    │  │                        │ │
│  │              │  │              │  │ • mart-bootstrap       │ │
│  │ • Kimball    │  │ • mart.yml   │  │ • dqc-audit            │ │
│  │   4-tier     │  │ • models/    │  │ • schema-evolve        │ │
│  │ • Bus matrix │  │ • seeds/     │  │ • mart-review          │ │
│  │ • DQC spec   │  │ • tests/     │  │                        │ │
│  │ • Naming     │  │ • pipeline/  │  │                        │ │
│  └──────────────┘  └──────────────┘  └────────────────────────┘ │
│                                                                  │
│  User: mart.yml ──► Builder Agent ──► Scaffolded Mart            │
│                          │                    │                   │
│                          ▼                    ▼                   │
│                    Reviewer Agent ◄── DQC Scorecard               │
│                          │                                        │
│                          ▼                                        │
│                    Pass/Fail Gate                                  │
├──────────────────────────────────────────────────────────────────┤
│                   dbt-core + dbt-duckdb                           │
├──────────────────────────────────────────────────────────────────┤
│               DuckDB (local) / MotherDuck (cloud)                │
└──────────────────────────────────────────────────────────────────┘
```

## Documentation

- [Bus Matrix](docs/bus-matrix.md) — Enterprise bus matrix design
- [DQC Framework](docs/dqc-framework.md) — Three-tier data quality contract specification
- [Naming Conventions](docs/naming-conventions.md) — Table, column, and model naming standards
- [Agent Orchestration](docs/agent-orchestration.md) — Multi-agent builder/reviewer workflow
- [Provider Abstraction](docs/provider-abstraction.md) — Warehouse-agnostic design with pluggable adapters
- [Methodology](METHODOLOGY.md) — Kimball fundamentals and framework philosophy

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add new mart templates or skills.

## License

[Apache License 2.0](LICENSE)
