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

| Capability | mart-forge | AltimateAI | Generic dbt Starter |
|---|---|---|---|
| **Kimball methodology built-in** | Yes — SCD types, conformed dims, bus matrix | No | No |
| **AI-assisted modeling** | Yes — agents suggest grain, dimensions, facts | No | No |
| **Template library** | Yes — reusable mart templates per domain | No | Minimal project scaffold |
| **Works without existing dbt project** | Yes — generates from scratch | No — requires existing project | Partial |
| **Methodology documentation** | Yes — auto-generated per mart | No | No |
| **Target warehouse** | DuckDB (local) / MotherDuck (cloud) | Snowflake, BigQuery, etc. | Any dbt adapter |

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

### Project Structure After Init

```
my-warehouse/
├── models/
│   ├── staging/          # Raw source → cleaned staging
│   ├── intermediate/     # Business logic transforms
│   └── marts/            # Kimball-modeled dimensional marts
│       ├── dim_*.sql     # Dimension tables (SCD handling built-in)
│       └── fct_*.sql     # Fact tables (grain documented)
├── seeds/                # Reference data
├── tests/                # Data quality assertions
├── docs/                 # Auto-generated methodology docs
│   └── bus_matrix.md     # Enterprise bus matrix
└── dbt_project.yml
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  mart-forge CLI                  │
├─────────────┬─────────────┬─────────────────────┤
│  Templates  │   Skills    │   Methodology Docs  │
│  (Jinja2)   │  (Claude)   │   (Auto-generated)  │
├─────────────┴─────────────┴─────────────────────┤
│              Scaffolding Engine                   │
│  ┌─────────┐ ┌──────────┐ ┌───────────────────┐ │
│  │ Kimball │ │ Template │ │  Grain + SCD      │ │
│  │ Rules   │ │ Registry │ │  Validator        │ │
│  └─────────┘ └──────────┘ └───────────────────┘ │
├──────────────────────────────────────────────────┤
│           dbt-core + dbt-duckdb                  │
├──────────────────────────────────────────────────┤
│         DuckDB (local) / MotherDuck (cloud)      │
└──────────────────────────────────────────────────┘
```

## Documentation

- [Methodology Guide](docs/methodology/) — Kimball fundamentals adapted for modern data stacks
- [Template Catalog](templates/) — Browse and customize mart templates
- [Skills Reference](skills/) — AI agent skills for assisted scaffolding
- [Examples](examples/) — End-to-end mart implementations

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add new mart templates or skills.

## License

[Apache License 2.0](LICENSE)
