---
name: mart-bootstrap
description: |
  Scaffold a complete Kimball data warehouse mart from a mart.yml config file. Creates full directory structure, all dbt model files (ODS/DIM/DWD/DWS/ADS), schema.yml with DQC tests, seeds, dqc_scorecard.json template, and GitHub Actions workflow.

  **Use when:**
  - "bootstrap a mart for {domain/source}"
  - "scaffold a new mart from mart.yml"
  - "create the dbt project for {domain}"
  - User provides or references a mart.yml and wants the full layer stack generated

  **Not for:**
  - Adding columns to an existing mart (use schema-evolve)
  - Auditing existing DQC coverage (use dqc-audit)
  - Reviewing production readiness (use mart-review)
---

# Mart Bootstrap

Reads a `mart.yml` configuration file and generates a complete Kimball-layered dbt project: directory structure, all model SQL files, schema.yml with generic tests implementing all 8 DQC control classes, dimension seeds, singular tests, dqc_scorecard.json template, and a GitHub Actions daily pipeline workflow.

## Constraints (read before doing anything)

- **Never fabricate provider schemas** -- if the mart.yml references a data source you don't know the schema for, generate a placeholder ODS with TODO columns and warn the user.
- **No hardcoded paths** -- all references use relative paths from repo root. Skills reference `docs/` for methodology and `templates/` for boilerplate.
- **Naming convention is mandatory** -- every model must follow `{prefix}_{layer}_{entity}` per the naming conventions doc. Violations make the mart fail `mart-review`.
- **Provenance columns on every ODS** -- `provider`, `pull_ts_utc`, `quote_ts_utc`, `run_id` are non-negotiable.
- **Unknown member row** -- every DIM must include a row ID = -1 with all attributes = 'Unknown', either via seed or model logic.

## Lifecycle Gates (checked before scaffolding begins)

This skill generates dbt models only after both design documents are approved. The full lifecycle:

1. `mart-forge init` → creates `mart.yml` + `business-requirements.md` template
2. `/mart-brd` → operator fills the BRD; both sign-off lines must reach `approved` or `approved-with-conditions` (Phase A gate)
3. `mart-forge tdd` (or `/mart-tdd`) → generates `tech-design-doc.md` (+ `sign-off-prd.md` as a summary); both TDD sign-off lines must reach `approved` or `approved-with-conditions` (Phase B gate)
4. `/mart-bootstrap` (this skill) → scaffolds the dbt project only after **both** gates pass

If either gate fails, STOP and inform the user which document is missing or unsigned. Route to `/mart-brd` if the BRD is missing/unapproved, or `/mart-tdd` if the TDD is missing/unapproved.

## Scaffold (only after both Phase A and Phase B gates pass)

Before executing any step below, verify **both gates**:

1. **Phase A gate:** `{mart_name}/business-requirements.md` exists and both sign-off lines have status `approved` or `approved-with-conditions`
2. **Phase B gate:** `{mart_name}/tech-design-doc.md` exists and both sign-off lines have status `approved` or `approved-with-conditions`

If either gate fails, STOP and inform the user which document is missing or unsigned.

## Workflow

1. **Read mart.yml** -> verify: confirm all required keys exist (`mart.name`, `mart.prefix`, `mart.grain`, `providers`, `schedule`, `dqc`)

2. **Create directory structure** -> verify: all directories exist
   ```
   {mart_name}/
   +-- models/
   |   +-- ods/
   |   +-- dim/
   |   +-- dwd/
   |   +-- dws/
   |   +-- ads/
   +-- seeds/
   +-- tests/
   +-- dbt_project.yml
   +-- profiles.yml
   +-- mart.yml
   +-- dqc_scorecard.json
   +-- .github/workflows/daily.yml
   ```

3. **Generate dimension seeds** -> verify: `seeds/dim_date.csv` covers required date range, entity seeds match mart.yml
   - `dim_date.csv`: date, day_of_week, is_weekend, month, quarter, year
   - Entity-specific seeds from mart.yml providers
   - Each seed must include an unknown member row (id=-1)

4. **Generate DIM models** -> verify: each has surrogate key, natural key, SCD strategy declared in schema.yml
   - `{prefix}_dim_date` -- role-playing date dimension from seed
   - Entity dimensions declared in mart.yml bus matrix
   - Every DIM: surrogate_key (PK), natural_key, attributes, `effective_from`/`effective_to`/`is_current` if SCD Type 2

5. **Generate ODS model** -> verify: explicit column list, provenance columns present
   ```sql
   select
       -- explicit column list (no SELECT *)
       column1,
       column2,
       -- provenance
       '{provider}' as provider,
       current_timestamp as pull_ts_utc,
       source_timestamp as quote_ts_utc,
       '{{ var("run_id", "manual") }}' as run_id
   from {{ ref('source_table') }}
   ```

6. **Generate DWD model** -> verify: business key dedup, grain declared in description, FK to all dims
   - Joins to DIMs via natural key -> surrogate key lookup
   - Grain documented in model description (schema.yml)
   - No `current_timestamp()` in logic -- use `pull_ts_utc` from ODS

7. **Generate DWS models** -> verify: aggregation windows match mart.yml grain, materialized as table
   - At minimum: `{prefix}_dws_daily_snapshot_1d` (daily summary)
   - Additional aggregations based on mart.yml metrics
   - Window suffix convention: `_1d`, `_nd`, `_td`, `_mtd`

8. **Generate ADS model** -> verify: one-big-table joining all relevant DWS/DWD, materialized as table
   - `{prefix}_ads_{consumer}_{purpose}` naming
   - Wide denormalized table for downstream consumption

9. **Generate schema.yml** -> verify: all 8 DQC control classes have at least one test per applicable model
   - PK Integrity: `not_null` + `unique` on every primary key
   - FK Integrity: `relationships` test for every foreign key
   - Freshness: source freshness or singular test on `pull_ts_utc`
   - Completeness: singular test for row count vs prior run
   - Accepted Ranges: `accepted_values` for enums, range tests for numerics
   - Duplicate Detection: singular test on business key uniqueness within grain window
   - Null-Rate: singular test for null percentage thresholds
   - Business Reconciliation: singular test comparing to external reference (from mart.yml `dqc.reconciliation`)

10. **Generate singular tests** -> verify: at least one per DQC control class that requires custom SQL
    - `tests/test_dqc_freshness.sql`
    - `tests/test_dqc_completeness.sql`
    - `tests/test_dqc_duplicate_detection.sql`
    - `tests/test_dqc_null_rate.sql`
    - `tests/test_dqc_accepted_ranges.sql`
    - `tests/test_dqc_reconciliation.sql`

11. **Generate dqc_scorecard.json template** -> verify: all 8 control classes listed, all status = "pending"

12. **Generate GitHub Actions workflow** -> verify: cron matches mart.yml schedule, steps = seed -> run -> test

13. **Generate dbt_project.yml** -> verify: correct name, profile, model paths, vars

## Output Checklist

- [ ] All directories created (`models/{ods,dim,dwd,dws,ads}`, `seeds/`, `tests/`)
- [ ] mart.yml copied/present at project root
- [ ] dbt_project.yml + profiles.yml generated
- [ ] At least 1 ODS model with provenance columns
- [ ] At least 1 DIM model with unknown member strategy
- [ ] At least 1 DWD fact model with declared grain
- [ ] At least 1 DWS aggregation with window suffix
- [ ] At least 1 ADS one-big-table
- [ ] schema.yml covers all 8 DQC control classes
- [ ] Singular tests exist for business-logic assertions
- [ ] dqc_scorecard.json template with all control classes
- [ ] GitHub Actions workflow with correct cron
- [ ] No hardcoded paths -- all relative from repo root
- [ ] No `SELECT *` in any model

## Resources

- `docs/naming-conventions.md` -- Model naming patterns and column conventions
- `docs/dqc-framework.md` -- DQC control class catalog and scorecard format
- `docs/bus-matrix.md` -- Bus matrix design and conformed dimensions
- `docs/dimensional-lifecycle.md` -- SCD types and unknown member patterns
- `templates/` -- Model SQL templates and mart.yml.template
- `examples/ecommerce-orders-mart/` -- Reference implementation
