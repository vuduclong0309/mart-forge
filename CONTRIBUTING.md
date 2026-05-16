# Contributing to mart-forge

Thank you for your interest in contributing! This guide covers how to add new mart templates and AI skills.

## Adding a New Mart Template

Mart templates live in `templates/` and are Jinja2-based dbt model generators.

### Structure

```
templates/
└── your-domain/
    ├── README.md              # Domain description, grain, dimensions, facts
    ├── dim_*.sql.j2           # Dimension model templates
    ├── fct_*.sql.j2           # Fact model templates
    ├── stg_*.sql.j2           # Staging model templates
    ├── schema.yml.j2          # dbt schema with tests
    └── bus_matrix_entry.yml   # Bus matrix contribution
```

### Steps

1. Fork the repo and create a branch: `git checkout -b template/your-domain`
2. Create a new directory under `templates/` named after your domain (e.g., `retail`, `saas-subscriptions`, `healthcare`)
3. Write your templates following the conventions below
4. Add a `README.md` documenting:
   - The business domain and use case
   - Grain of each fact table
   - Dimension descriptions and SCD types
   - Required source data schema
5. Add a `bus_matrix_entry.yml` listing the facts and dimensions your template provides
6. Add an example in `examples/` showing your template applied to sample data
7. Open a PR with the prefix `template:` (e.g., `template: add retail domain`)

### Template Conventions

- Dimension tables: prefix with `dim_`, declare SCD type in the README
- Fact tables: prefix with `fct_`, document grain in a comment at the top of the template
- Staging models: prefix with `stg_`, one per source table
- Use Jinja2 variables for configurable parts (source schema, table names, date columns)
- Include dbt tests for grain enforcement (unique + not_null on grain columns)

## Adding a New Skill

Skills are Claude Code agent capabilities that live in `skills/`.

### Structure

```
skills/
└── your-skill/
    ├── README.md              # Skill description and usage
    ├── prompt.md              # System prompt for the skill
    └── examples/              # Example inputs and outputs
```

### Steps

1. Fork the repo and create a branch: `git checkout -b skill/your-skill`
2. Create a new directory under `skills/`
3. Write a `prompt.md` that instructs the agent on how to perform the skill
4. Add a `README.md` with usage instructions
5. Include at least one example showing input and expected output
6. Open a PR with the prefix `skill:` (e.g., `skill: add grain advisor`)

## General Guidelines

- Run `dbt build` on any template changes to verify they produce valid SQL
- Follow the naming conventions in [METHODOLOGY.md](METHODOLOGY.md)
- Keep templates focused on a single domain — don't combine unrelated domains
- Write clear commit messages describing what the template/skill does

## Code of Conduct

Be respectful and constructive. We're building something useful together.
