---
name: mart-tdd
description: |
  Generate a Tech Design Document (TDD) with column-level calculation specs for a mart. The TDD is the Phase B gate artifact — no dbt model code is scaffolded until the TDD is signed off.

  **Use when:**
  - "create a tech design for {mart}"
  - "write TDD for {mart}"
  - "design the physical schema for {mart}"
  - User has an approved BRD and wants to specify column-level calculations before code generation
  - Phase A (BRD sign-off) is complete and the user wants Phase B design

  **Not for:**
  - Scaffolding directory structure or generating dbt code (use mart-bootstrap after TDD sign-off)
  - Reviewing existing models (use mart-review)
  - Auditing DQC coverage (use dqc-audit)
---

# Mart TDD (Tech Design Document)

Reads an approved `business-requirements.md` (BRD) and `mart.yml` to produce a Tech Design Document with physical table schemas, column-level calculation specs, source-to-target mappings, and a traceability matrix. The TDD is the **Phase B gate** — `mart-bootstrap` must not generate any model code until the TDD is signed off.

## HARD GATE

**No scaffold until TDD signed off.** The `mart-bootstrap` Phase B workflow must verify that:

1. `{mart_name}/business-requirements.md` exists with both sign-off lines approved (Phase A gate)
2. `{mart_name}/tech-design-doc.md` exists with both sign-off lines approved (Phase B gate)

If either gate fails, STOP and inform the user which document is missing or unsigned.

## Constraints (read before doing anything)

- **Every column must have a calculation** — the `calculation` column in the physical schema tables is the core deliverable. No column may have an empty or placeholder calculation. If the calculation is unknown, write `TODO: <what needs to be determined>` and flag it in the traceability matrix as unresolved.
- **Bidirectional traceability is mandatory** — Section 8 must map every TDD metric forward to the model file and line number that will implement it, and every SQL expression backward to the TDD section that specifies it. Until code exists, use planned file paths from `docs/naming-conventions.md`.
- **Kimball 4-step must be completed** — Section 1 forces the designer to walk through business process selection, grain declaration, dimension identification, and fact identification before touching physical schemas. Skipping this produces marts that violate grain or miss conformed dimensions.
- **Source-to-target before physical schema** — Section 3 traces raw source fields through each layer. The physical schema (Section 4) then references these transforms. This order prevents inventing columns that have no source.
- **DQC plan references the approved BRD** — Section 5 control thresholds must match the tolerances declared in `business-requirements.md`. Any deviation must be documented with rationale.
- **No confidential data** — This is an open-source framework. Use generic Kimball terminology. Do not reference proprietary systems, credentials, or internal data sources.

## Workflow

### Prerequisites

Before starting, verify:

1. `{mart_name}/mart.yml` exists and passes schema validation
2. `{mart_name}/business-requirements.md` exists with both sign-off lines `approved` or `approved-with-conditions`
3. Source system schema is known (either from provider docs, a sample pull, or the ODS placeholder from Phase A)

### Step 1 — Read inputs

- Parse `mart.yml` for mart metadata (name, prefix, grain, providers, schedule, dqc config)
- Parse `business-requirements.md` for approved business context (personas, grain, bus matrix, DQC controls, sensitivity)
- Read `docs/naming-conventions.md` for model and column naming rules
- Read `docs/dqc-framework.md` for control class specifications
- Read `docs/bus-matrix.md` for conformed dimension patterns
- If source system documentation exists, read it for field-level schema

### Step 2 — Design reasoning (Kimball 4-step)

Fill Section 1 of the TDD template:

1. **Select the business process** — name the operational process, not the source system
2. **Declare the grain** — use the grain from `mart.yml`, verify it matches the BRD
3. **Identify the dimensions** — list all dimensions from the bus matrix section of the PRD, note SCD type and conformance status
4. **Identify the facts** — enumerate all metrics/measures, classify as additive/semi-additive/non-additive, note units

### Step 3 — Bus matrix

Fill Section 2: cross-reference business processes against dimensions. Mark each intersection.

### Step 4 — Source-to-target mapping

Fill Section 3: for each layer (ODS, DIM, DWD, DWS, ADS), document every source field, its target column, and the transform applied. ODS must include provenance columns (provider, pull_ts_utc, quote_ts_utc, run_id).

### Step 5 — Physical table schemas

Fill Section 4: for each model, document every column with:

| Field | Requirement |
|-------|-------------|
| column_name | snake_case per naming conventions |
| data_type | Warehouse-agnostic type (VARCHAR, INTEGER, DOUBLE, DATE, TIMESTAMP, BOOLEAN) |
| role | PK, FK, NK, DD, M, A, or P |
| definition | Human-readable description |
| example_value | Representative value from the domain |
| calculation | **Exact SQL expression or derivation logic** |
| data_source | Source model or external system |

Role abbreviations:
- **PK** — Primary key
- **FK** — Foreign key (references a DIM surrogate key)
- **NK** — Natural key (from source system)
- **DD** — Degenerate dimension (dimension attribute stored in fact table)
- **M** — Measure / metric
- **A** — Attribute
- **P** — Provenance column

### Step 6 — DQC plan

Fill Section 5:

1. Build the control coverage matrix (model x control class)
2. For each test, specify: test type (generic/singular), file location, assertion logic, tolerance, severity
3. Cross-check thresholds against `business-requirements.md`

### Step 7 — Refresh and monitoring

Fill Sections 6 and 7:

- Refresh strategy: cron, timezone, materialization per model, dependency graph
- Monitoring: pipeline health signals, DQC alert thresholds, scorecard review cadence

### Step 8 — Traceability matrix

Fill Section 8: bidirectional mapping between TDD specs and planned SQL files.

- Forward: TDD section + column -> model file + line reference (use planned paths if code doesn't exist yet)
- Backward: model file + column -> TDD section + column name

### Step 9 — Review and sign-off

Present the completed TDD for review. Both sign-off lines must be `approved` or `approved-with-conditions` before `mart-bootstrap` Phase B proceeds.

## Output Checklist

- [ ] Changelog filled with version, date, author
- [ ] Kimball 4-step completed (business process, grain, dimensions, facts)
- [ ] Bus matrix filled with all dimension intersections
- [ ] Source-to-target mapping covers all layers (ODS through ADS)
- [ ] Physical schema has every column with a non-empty `calculation` field
- [ ] All ODS models have provenance columns (provider, pull_ts_utc, quote_ts_utc, run_id)
- [ ] All DIM models document unknown member row (ID = -1)
- [ ] DQC plan covers all 8 control classes with specific thresholds
- [ ] DQC thresholds match BRD acceptance criteria
- [ ] Refresh strategy includes materialization per model and dependency graph
- [ ] Monitoring plan covers pipeline health and DQC alerting
- [ ] Traceability matrix is bidirectional (TDD -> SQL, SQL -> TDD)
- [ ] No empty or placeholder calculations (flag as TODO if unknown)
- [ ] No confidential references — generic Kimball terminology only
- [ ] Sign-off section present with pending status

## Resources

- `templates/tech-design-doc.template.md` — TDD template
- `templates/business-requirements.template.md` — BRD template (Phase A prerequisite)
- `docs/naming-conventions.md` — Model and column naming standards
- `docs/dqc-framework.md` — DQC control class catalog
- `docs/bus-matrix.md` — Bus matrix design patterns
- `docs/dimensional-lifecycle.md` — SCD types and unknown member patterns
- `examples/gme-options-mart/` — Reference implementation with completed TDD
