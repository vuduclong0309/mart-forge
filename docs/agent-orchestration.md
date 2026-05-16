# Agent Orchestration

mart-forge uses AI agents organized in a builder-reviewer pattern to scaffold, validate, and evolve data marts. This guide describes the agent architecture, issue lifecycle, and dispatch coordination.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [The Builder-Reviewer Pattern](#the-builder-reviewer-pattern)
- [Agent Skills](#agent-skills)
- [Issue Lifecycle](#issue-lifecycle)
- [Dispatch Waves](#dispatch-waves)
- [Conflict Resolution](#conflict-resolution)
- [Human-in-the-Loop Gates](#human-in-the-loop-gates)
- [Running Agents Locally](#running-agents-locally)

---

## Architecture Overview

mart-forge orchestration is inspired by the [OpenAI Swarm/Symphony](https://github.com/openai/swarm) pattern: specialized agents with clear boundaries, handoff protocols, and a shared artifact space (the dbt project on disk).

```
                    +--------------------+
                    |    Orchestrator     |
                    |  (human or script)  |
                    +---------+----------+
                              |
              +---------------+---------------+
              |                               |
     +--------v--------+            +--------v--------+
     |   Builder Agent  |            |  Reviewer Agent  |
     |  (mart-bootstrap |            |  (mart-review    |
     |   schema-evolve) |            |   dqc-audit)     |
     +--------+---------+            +--------+---------+
              |                               |
              +---------- Shared ----------+
              |        File System          |
              | (models/, tests/, schema.yml|
              |  dqc_scorecard.json)        |
              +-----------------------------+
```

### Key Principles

1. **Separation of concerns** -- The agent that builds a mart never reviews it. The reviewer is adversarial by design.
2. **Artifact-mediated communication** -- Agents communicate through files on disk (SQL models, schema.yml, dqc_scorecard.json), not through message passing.
3. **Idempotent operations** -- Running any agent twice on the same input produces the same output.
4. **Human gates** -- Agents cannot promote a mart to production. Human sign-off is required at G5.

---

## The Builder-Reviewer Pattern

### Builder Agent

The builder agent creates and modifies mart artifacts. It has two skills:

| Skill | Purpose | Input | Output |
|-------|---------|-------|--------|
| `mart-bootstrap` | Create a new mart from scratch | `mart.yml` config | Full dbt project (models, tests, seeds, CI) |
| `schema-evolve` | Add a column to an existing mart | Column name, type, mart ID | Updated ODS/DWD models, schema.yml, tests |

**Builder constraints:**
- Never skips the unknown member row in dimensions
- Never uses `SELECT *` -- explicit column lists only
- Never uses `current_timestamp()` in model logic
- Always adds the 4 provenance columns to ODS
- Always adds at least one test per new column

### Reviewer Agent

The reviewer agent validates mart quality with an adversarial posture. It has two skills:

| Skill | Purpose | Input | Output |
|-------|---------|-------|--------|
| `mart-review` | Full production readiness review | Mart directory path | Graded scorecard (A-F), review_report.json |
| `dqc-audit` | DQC coverage analysis | Mart directory path | Coverage matrix, gap list, verdict |

**Reviewer constraints:**
- Assumes problems exist until proven otherwise
- Checks every model, not just new ones
- Grades honestly -- no inflated scores to avoid friction
- Produces machine-readable artifacts (`review_report.json`) for CI gates

### Why Separate Agents?

Combining build and review in a single agent creates a conflict of interest. The builder is optimized to produce working code quickly. The reviewer is optimized to find problems. When the same agent does both, it tends to:

- Skip tests for code it just wrote (false confidence)
- Downgrade severity of issues it caused (self-bias)
- Overlook structural problems because it understands the intent (curse of knowledge)

The builder-reviewer split forces a fresh adversarial pass on every change.

---

## Agent Skills

### mart-bootstrap

**Trigger:** "bootstrap a mart for {domain}", "scaffold a new mart from mart.yml"

**Workflow:**
1. Read and validate `mart.yml`
2. Create directory structure (models/ods, dim, dwd, dws, ads + seeds + tests)
3. Generate dimension seeds (dim_date.csv with calendar data, unknown member rows)
4. Generate DIM models (surrogate keys, SCD handling, unknown members)
5. Generate ODS models (explicit column list, provenance columns)
6. Generate DWD models (grain declaration, FK joins to all DIMs)
7. Generate DWS models (aggregations with window suffixes)
8. Generate ADS models (one-big-table for consumers)
9. Generate schema.yml (column docs + all 8 DQC control class tests)
10. Generate singular tests (freshness, completeness, duplicates, null-rate, reconciliation)
11. Generate dqc_scorecard.json template
12. Generate GitHub Actions workflow

**Output:** A complete dbt project that builds and passes `dbt test` on first run.

### dqc-audit

**Trigger:** "audit DQC coverage for {mart}", "what DQC controls are missing?"

**Workflow:**
1. Inventory all models by layer
2. Parse schema.yml for generic tests (not_null, unique, relationships, accepted_values)
3. Read tests/ directory for singular tests and classify by control class
4. Check dqc_scorecard.json health
5. Build coverage matrix (model x control class)
6. Identify untested columns
7. Score and rank gaps by severity

**Output:** Coverage matrix, gap list (CRITICAL to LOW), verdict (PASS/PARTIAL/FAIL).

### schema-evolve

**Trigger:** "add column {name} to {mart}", "source schema changed, propagate to warehouse"

**Workflow:**
1. Locate the target ODS model
2. Add column to ODS explicit SELECT list
3. Classify column (business attribute vs. technical metadata)
4. Propagate to DWD if business attribute
5. Add appropriate tests
6. Update schema.yml documentation

**Output:** Updated models and tests, migration notes.

### mart-review

**Trigger:** "review {mart} for production readiness", "is the mart ready to ship?"

**Workflow:**
1. Inventory all models, tests, and config files
2. Validate naming conventions against patterns
3. Check bus matrix coverage (fact tables reference declared dimensions)
4. Verify grain declarations in schema.yml
5. Audit incremental strategy (no idempotency violations)
6. Check provenance columns on all ODS models
7. Validate dimension lifecycle (SCD types, unknown members)
8. Run full DQC audit (all 8 control classes)
9. Check pipeline configuration (GitHub Actions matches mart.yml)
10. Assign grade (A-F) based on findings

**Output:** Graded scorecard, finding list by severity, review_report.json.

---

## Issue Lifecycle

When an agent identifies a problem, it follows this lifecycle:

```
DETECTED -> CLASSIFIED -> REPORTED -> ASSIGNED -> RESOLVED -> VERIFIED
```

### States

| State | Description | Who Acts |
|-------|-------------|----------|
| DETECTED | Agent finds a potential issue during audit/review | Reviewer agent |
| CLASSIFIED | Issue assigned severity (Critical/High/Medium/Low) and category | Reviewer agent |
| REPORTED | Issue documented in review output or scorecard | Reviewer agent |
| ASSIGNED | Issue assigned to builder agent or human for resolution | Orchestrator |
| RESOLVED | Fix applied (model updated, test added, etc.) | Builder agent or human |
| VERIFIED | Re-review confirms the fix resolves the issue | Reviewer agent |

### Severity Levels

| Severity | Impact | Examples | SLA |
|----------|--------|----------|-----|
| Critical | Data integrity at risk | Missing PK test, `current_timestamp()` in model, multi-grain fact | Fix before any other work |
| High | Production incident likely | Missing FK integrity, no freshness check, `SELECT *` | Fix before G4 review |
| Medium | Technical debt | Missing null-rate tests, non-standard naming | Fix before G5 production |
| Low | Style/documentation | Missing model description, inconsistent aliases | Fix when convenient |

### Category Tags

Issues are tagged with categories to group related findings:

| Category | Scope |
|----------|-------|
| `naming` | Model or column naming convention violation |
| `grain` | Grain declaration missing, ambiguous, or violated |
| `incremental` | Idempotency violation or missing incremental guard |
| `provenance` | Missing or incorrect provenance columns |
| `dqc` | Missing DQC control class coverage |
| `bus_matrix` | Dimension not referenced or not conformed |
| `lifecycle` | SCD type undeclared, unknown member missing |
| `pipeline` | CI/CD configuration issue |

---

## Dispatch Waves

When orchestrating multiple agents (e.g., bootstrapping several marts or reviewing an entire warehouse), work is organized into waves.

### Wave 1: Build

All builder tasks run in parallel. Each mart is independent, so multiple `mart-bootstrap` invocations can proceed simultaneously.

```
Wave 1 (parallel):
  +-- mart-bootstrap(mart_a.yml)
  +-- mart-bootstrap(mart_b.yml)
  +-- mart-bootstrap(mart_c.yml)
```

### Wave 2: Build Verification

After builders complete, run `dbt build` on each mart to verify compilation and data loading.

```
Wave 2 (per-mart, sequential within mart):
  +-- dbt seed (mart_a)
  +-- dbt run  (mart_a)
  +-- dbt test (mart_a)
```

### Wave 3: Review

Reviewer agents run after build verification. Each review is independent.

```
Wave 3 (parallel):
  +-- mart-review(mart_a)
  +-- mart-review(mart_b)
  +-- mart-review(mart_c)
```

### Wave 4: Remediation

Builder agents fix issues identified by reviewers. This wave may iterate multiple times until all issues are resolved.

```
Wave 4 (per-issue):
  +-- schema-evolve(mart_a, fix_issue_1)
  +-- schema-evolve(mart_b, fix_issue_2)
  +-- ... re-review after fixes ...
```

### Wave 5: Sign-Off

Human reviews the final grades and approves promotion to production.

### Orchestration Script Example

```bash
#!/bin/bash
# Example orchestration script for CI

# Wave 1: Bootstrap (skip if marts already exist)
for config in marts/*/mart.yml; do
  mart_dir=$(dirname "$config")
  if [ ! -f "$mart_dir/dbt_project.yml" ]; then
    claude --skill mart-bootstrap "$config" &
  fi
done
wait

# Wave 2: Build verification
for mart_dir in marts/*/; do
  cd "$mart_dir"
  dbt seed && dbt run && dbt test
  cd -
done

# Wave 3: Review
for mart_dir in marts/*/; do
  claude --skill mart-review "$mart_dir" &
done
wait

# Wave 4: Check results
for report in marts/*/review_report.json; do
  grade=$(jq -r '.grade' "$report")
  if [ "$grade" = "F" ] || [ "$grade" = "D" ]; then
    echo "BLOCKED: $(dirname $report) got grade $grade"
    exit 1
  fi
done

echo "All marts passed review."
```

---

## Conflict Resolution

When multiple agents modify the same mart (e.g., two `schema-evolve` operations), conflicts are resolved through file-level locking:

### Rules

1. **One writer per mart at a time** -- Never run two builder skills on the same mart directory concurrently
2. **Reviewers are read-only** -- Review and audit skills never modify files, so they can run concurrently with each other (but not with builders)
3. **Last write wins** on schema.yml -- If two schema-evolve operations add columns, they must be serialized to avoid YAML merge conflicts
4. **dqc_scorecard.json is append-only** -- Each control class entry is updated independently; concurrent updates to different classes are safe

### Preventing Conflicts

- Use the wave pattern (all builds complete before any reviews start)
- In CI, run each mart in its own job with artifact passing between stages
- For interactive use, run one skill at a time per mart

---

## Human-in-the-Loop Gates

Agents cannot make every decision autonomously. The following situations require human input:

### Mandatory Human Gates

| Gate | Trigger | Human Action Required |
|------|---------|----------------------|
| G5 Production Sign-Off | Mart passes G4 review | Approve or reject promotion |
| New Dimension Decision | `schema-evolve` detects a new FK target | Confirm: create new DIM or map to existing? |
| Breaking Change | Column removal or grain change requested | Confirm: proceed or abort? |
| Reconciliation Failure | Business reconciliation test fails | Investigate: data issue or test threshold wrong? |

### Optional Human Gates

| Gate | Trigger | Default If No Human Input |
|------|---------|---------------------------|
| Column Classification | Ambiguous business vs. technical attribute | Default: propagate to DWD |
| SCD Type Selection | New dimension with unclear change history needs | Default: Type 1 |
| Threshold Tuning | Null-rate or completeness threshold too strict/loose | Default: 5% null-rate, 50% volume |

---

## Running Agents Locally

### With Claude Code

```bash
# Bootstrap a new mart
claude "bootstrap a mart from mart.yml"

# Review an existing mart
claude "review examples/ecommerce-orders-mart for production readiness"

# Audit DQC coverage
claude "audit DQC coverage for examples/ecommerce-orders-mart"

# Evolve schema
claude "add column discount_pct (double) to the ecommerce mart"
```

### With Skills Directly

```bash
# If skills are installed in .claude/skills/
claude --skill mart-bootstrap
claude --skill mart-review
claude --skill dqc-audit
claude --skill schema-evolve
```

### CI Integration

See `.github/workflows/ecommerce-mart-ci.yml` for an example of running `dbt seed + run + test` in GitHub Actions. The review and audit skills can be added as additional CI steps that parse `review_report.json` and `dqc_scorecard.json` to enforce quality gates.

---

## Checklist for Setting Up Orchestration

- [ ] `mart.yml` defined for each mart in the warehouse
- [ ] Builder skills available (`mart-bootstrap`, `schema-evolve`)
- [ ] Reviewer skills available (`mart-review`, `dqc-audit`)
- [ ] CI pipeline configured with seed -> run -> test stages
- [ ] Quality gate enforcement on `review_report.json` grade
- [ ] Human sign-off process defined for G5
- [ ] Conflict resolution rules documented for multi-agent scenarios
