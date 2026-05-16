<p align="center">
  <h1 align="center">mart-forge</h1>
  <p align="center">
    Methodology-first Kimball data warehouse scaffolding via AI agents
  </p>
</p>

<p align="center">
  <a href="https://github.com/vuduclong0309/mart-forge/actions"><img src="https://img.shields.io/github/actions/workflow/status/vuduclong0309/mart-forge/ci.yml?branch=main&label=CI" alt="CI Status"></a>
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

Existing tools like [AltimateAI](https://github.com/AltimateAI/altimate-code) focus on optimizing *existing* dbt projects — linting, documentation, and testing for code that's already written. They're excellent at what they do, but they don't help you **design** the warehouse in the first place.

## What mart-forge Does

mart-forge is an **opinionated, methodology-first framework** that pairs Kimball dimensional modeling best practices with AI agents to scaffold production-grade data marts from the ground up.

| | AltimateAI (altimate-code) | mart-forge |
|---|---|---|
| **Focus** | Deterministic DE tooling for existing dbt projects (lint, lineage, FinOps, validation) | Kimball scaffolding + review methodology for new marts |
| **Input** | An existing dbt project | `mart.yml` config + data source contract |
| **Output** | Better SQL, docs, lineage, anti-pattern detection | Scaffolded Kimball mart (ODS → DIM → DWD → DWS → ADS) + DQC scorecard |
| **Agent model** | Single agent running 100+ deterministic tools | Multi-agent: builder scaffolds, reviewer audits with enforceable gates |
| **Knowledge base** | Generic SQL patterns, broad warehouse coverage (10+) | Opinionated Kimball methodology, narrow warehouse coverage (dbt-duckdb in v1) |
| **Quality** | Anti-pattern detection, lineage validation | Control-catalog DQC with reconciliation + machine-readable gate artifacts |

## Quick Start

### Prerequisites

- Python 3.10+
- [dbt-core](https://docs.getdbt.com/docs/core/installation) with dbt-duckdb adapter
- [Claude Code](https://claude.ai/claude-code) (for AI-assisted scaffolding)

### Installation

```bash
pip install mart-forge
```

### Scaffold Your First Mart

```bash
# Initialize a new mart-forge project
mart-forge init my-warehouse

# Use an AI agent to scaffold a mart from a data domain description
cd my-warehouse
mart-forge scaffold --domain "e-commerce orders" --template retail

# Or run interactively with Claude Code
claude --skill mart-forge
```

### What Gets Scaffolded

A `mart.yml` config produces a complete dbt project with Kimball 4-tier layers:

```
my-mart/
├── mart.yml                  # Your domain config
├── models/
│   ├── ods/                  # Operational Data Store — raw ingestion
│   ├── dim/                  # Dimensions — conformed, SCD-aware
│   ├── dwd/                  # Detail facts — atomic grain
│   ├── dws/                  # Summary facts — aggregated
│   └── ads/                  # Application Data Service — one-big-table
├── seeds/
│   └── dim_date.csv          # Reference date dimension
├── tests/                    # Grain enforcement + business logic
├── dqc_scorecard.json        # Machine-readable quality gate
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
