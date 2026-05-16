---
name: mart-review
description: |
  Review a Kimball mart for production readiness. Validates naming conventions, bus matrix coverage, grain declarations, incremental strategy, provenance columns, and runs a full DQC audit. Outputs a graded readiness scorecard (A/B/C/D/F) with actionable findings.

  **Use when:**
  - "review {mart} for production readiness"
  - "is the mart ready to ship?"
  - "run the reviewer agent checks on {mart}"
  - "grade the warehouse quality"
  - Before promoting a mart past the review gate (G4 in the quality gate spec)

  **Not for:**
  - Building a mart (use mart-bootstrap)
  - Adding columns (use schema-evolve)
  - Just checking DQC coverage (use dqc-audit for that alone)
---

# Mart Review

Adversarial review of a Kimball mart for production readiness. Assumes the builder's code has bugs. Validates naming conventions, bus matrix coverage, grain discipline, incremental strategy, idempotency, provenance, and full DQC coverage. Produces a graded scorecard and a machine-readable `review_report.json` artifact.

## Constraints (read before doing anything)

- **Adversarial posture** -- assume problems exist until proven otherwise. A clean review means you checked, not that you skipped.
- **Source-tag findings** -- mark each finding as [VERIFIED] (confirmed by reading code) or [SUSPECTED] (pattern suggests issue but couldn't fully confirm).
- **Machine-readable output required** -- the `review_report.json` artifact is consumed by quality gates. It must be valid JSON matching the schema below.
- **Grade honestly** -- an A-grade mart has zero Critical/High findings. Don't grade generously to avoid conflict.

## Workflow

1. **Locate and inventory the mart** -> verify: find all model files, schema.yml, tests, mart.yml, dbt_project.yml
   - Count models per layer (ODS/DIM/DWD/DWS/ADS)
   - Verify directory structure matches convention
   - Check mart.yml exists and is parseable

2. **Validate naming conventions** -> verify: every model file follows `{prefix}_{layer}_{entity}` pattern

   Rules (from docs/naming-conventions.md):
   | Layer | Pattern | Materialization |
   |-------|---------|-----------------|
   | ODS | `{prefix}_ods_{source}_{entity}` | view or incremental |
   | DIM | `{prefix}_dim_{entity}` | table |
   | DWD | `{prefix}_dwd_{grain}_{entity}_di` | table or incremental |
   | DWS | `{prefix}_dws_{dims}_{metric}_{window}` | table |
   | ADS | `{prefix}_ads_{consumer}_{purpose}` | table |

   Window suffixes: `_1d`, `_nd`, `_td`, `_mtd`

   Check:
   - File names match their directory (ods/ contains only ods models)
   - Prefix is consistent across all models
   - Materialization config matches layer convention
   - DWS models have valid window suffix

3. **Check bus matrix coverage** -> verify: fact tables reference all declared dimensions
   - Does a bus matrix exist (in schema.yml descriptions or standalone doc)?
   - Do DWD fact tables JOIN to all dimensions in the bus matrix?
   - Are conformed dimensions actually shared (not duplicated)?
   - Is `dim_date` present and role-playing where needed?

4. **Verify grain declarations** -> verify: every DWD model has exactly one declared grain
   - Check schema.yml model descriptions for grain statement
   - Verify PK composite matches declared grain
   - No multi-grain fact tables (if detected, flag as CRITICAL)

5. **Audit incremental strategy** -> verify: no idempotency violations

   Check for violations:
   - `current_timestamp()` or `now()` in model logic (CRITICAL -- breaks idempotency)
   - `SELECT *` anywhere (HIGH -- schema drift undetectable)
   - DWS/ADS using incremental instead of table (MEDIUM -- aggregations should rebuild)

6. **Check provenance columns** -> verify: every ODS model has all 4 required columns
   - `provider` -- source identifier
   - `pull_ts_utc` -- ingestion timestamp
   - `quote_ts_utc` -- source data timestamp
   - `run_id` -- pipeline trace identifier

   Missing any = HIGH finding.

7. **Validate dimension lifecycle** -> verify: SCD strategy declared, unknown member exists
   - Each DIM declares SCD type (0/1/2) in schema.yml
   - SCD Type 2 dims have `effective_from`, `effective_to`, `is_current` columns
   - Unknown member row strategy defined (row with sk=-1)
   - Late-arriving data handling documented

8. **Run DQC audit** -> verify: invoke dqc-audit logic and incorporate results
   - All 8 control classes checked
   - Coverage matrix generated
   - Gaps identified and incorporated into findings

9. **Check pipeline configuration** -> verify: GitHub Actions workflow exists and matches mart.yml
   - Cron schedule matches mart.yml
   - Steps: seed -> run -> test (in order)
   - Fail-fast behavior configured
   - No secrets hardcoded in workflow

10. **Score and produce artifacts** -> verify: grade calculated, review_report.json valid

## Grading Rubric

| Grade | Criteria |
|-------|----------|
| **A** | Zero Critical or High findings. All 8 DQC controls pass. Bus matrix complete. |
| **B** | Zero Critical. <=2 High findings. DQC >=6/8 controls covered. |
| **C** | Zero Critical. <=4 High findings. DQC >=4/8 controls covered. |
| **D** | <=1 Critical. Multiple High findings. DQC partial. |
| **F** | Multiple Critical findings. DQC absent or severely lacking. |

## Severity Definitions

| Severity | Meaning | Examples |
|----------|---------|---------|
| **Critical** | Data integrity at risk, pipeline will produce wrong results | Multi-grain fact, no PK test, `current_timestamp()` in logic |
| **High** | Governance gap, production incident likely | Missing FK integrity, no freshness check, `SELECT *` |
| **Medium** | Best practice violation, technical debt | Missing null-rate tests, non-standard naming, DWS as incremental |
| **Low** | Style/documentation issue | Missing model description, inconsistent alias convention |

## Output Checklist

- [ ] Naming convention audit (all models checked)
- [ ] Bus matrix coverage verified
- [ ] Grain declarations verified (every DWD)
- [ ] Incremental strategy audited (no idempotency violations)
- [ ] Provenance columns checked (every ODS)
- [ ] Dimension lifecycle reviewed (SCD + unknown member)
- [ ] DQC audit completed (8 control classes)
- [ ] Pipeline configuration validated
- [ ] Grade assigned with justification
- [ ] review_report.json artifact produced
- [ ] Findings sorted by severity

## Output Format

```
## Mart Review -- {mart_name}

### Summary
- Grade: {A|B|C|D|F}
- Models reviewed: {count}
- Findings: {critical}C / {high}H / {medium}M / {low}L
- DQC coverage: {X}/8 control classes

### Findings (by severity)

#### Critical
1. [{category}] {description} -- model: {model_name}

#### High
...

#### Medium
...

#### Low
...

### DQC Coverage Matrix
{from dqc-audit output}

### Recommendation
{approve | approve_with_notes | request_changes | reject}

### Next Steps
1. {highest priority fix}
2. {second priority}
...
```

## review_report.json Schema

```json
{
  "mart": "{mart_name}",
  "reviewer": "mart-review",
  "reviewed_at": "{ISO8601}",
  "grade": "{A|B|C|D|F}",
  "max_severity": "{critical|high|medium|low|none}",
  "findings": [
    {
      "severity": "{critical|high|medium|low}",
      "category": "{naming|grain|incremental|provenance|dqc|bus_matrix|lifecycle|pipeline}",
      "model": "{model_name or null}",
      "description": "{what's wrong}",
      "remediation": "{how to fix}"
    }
  ],
  "dqc_coverage": {
    "classes_covered": 0,
    "classes_total": 8,
    "details": {}
  },
  "recommendation": "{approve|approve_with_notes|request_changes|reject}"
}
```

## Resources

- `docs/naming-conventions.md` -- Model naming patterns
- `docs/bus-matrix.md` -- Bus matrix design and conformance rules
- `docs/dimensional-lifecycle.md` -- SCD types and unknown member patterns
- `docs/dqc-framework.md` -- DQC control classes and quality gates
- `docs/agent-orchestration.md` -- Builder-reviewer pattern and grade rubric
- `dqc-audit` skill -- invoked as sub-check for DQC coverage
