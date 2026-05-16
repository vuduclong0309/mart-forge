---
name: dqc-audit
description: |
  Audit Data Quality Contract coverage for a Kimball mart. Validates all 8 control classes are implemented per model, checks dqc_scorecard.json health, identifies untested columns and missing tests, outputs a coverage matrix with gap analysis.

  **Use when:**
  - "audit DQC coverage for {mart}"
  - "check test coverage on the warehouse"
  - "what DQC controls are missing?"
  - "validate quality gates for {mart}"
  - Before promoting a mart to production (pre-review check)

  **Not for:**
  - Building a mart from scratch (use mart-bootstrap)
  - Adding a new column (use schema-evolve)
  - Full production readiness review (use mart-review, which calls this skill internally)
---

# DQC Audit

Validates that a mart implements all 8 required Data Quality Contract control classes from the mart-forge framework. Produces a coverage matrix showing which controls exist per model, identifies gaps, and outputs a severity-ranked remediation list.

## Constraints (read before doing anything)

- **All 8 control classes are mandatory** -- a mart cannot pass audit with any class at 0% coverage. "Not applicable" is never valid for PK/FK/freshness/duplicates on fact tables.
- **dqc_scorecard.json is authoritative** -- if it doesn't exist or has `fail`/`unavailable` entries, the audit CANNOT pass. Two consecutive `unavailable` results = `error` on third run.
- **Read schema.yml AND tests/ directory** -- generic tests live in schema.yml, singular tests in tests/. Both count toward coverage. Don't miss either source.
- **Source-tag your assessment** -- mark coverage findings as [VERIFIED] (test file exists and SQL is valid) or [INFERRED] (schema.yml declares test but you haven't validated SQL correctness).

## Workflow

1. **Locate the mart** -> verify: find `mart.yml` or `dbt_project.yml` to identify the mart root, prefix, and model inventory
   - List all `.sql` files under `models/` grouped by layer (ods/dim/dwd/dws/ads)
   - Extract model names and their layer classification

2. **Inventory generic tests (schema.yml)** -> verify: parse every `schema.yml` under models/ for test declarations
   - For each model, extract:
     - `not_null` tests -> contributes to PK Integrity
     - `unique` tests -> contributes to PK Integrity
     - `relationships` tests -> contributes to FK Integrity
     - `accepted_values` tests -> contributes to Accepted Ranges
   - Map each test to its DQC control class

3. **Inventory singular tests (tests/)** -> verify: read each `.sql` file in tests/ and classify by control class
   - Freshness tests: look for `pull_ts_utc` / `max(timestamp)` comparisons
   - Completeness tests: look for row count comparisons vs prior run
   - Duplicate Detection: look for `GROUP BY ... HAVING COUNT(*) > 1`
   - Null-Rate: look for `COUNT(*) FILTER (WHERE col IS NULL) / COUNT(*)`
   - Business Reconciliation: look for external value comparisons with tolerance

4. **Check dqc_scorecard.json** -> verify: file exists, parse status of each control
   - All 8 classes present?
   - Any `fail` status? -> report as CRITICAL gap
   - Any `unavailable` status? -> report as WARNING (check consecutive count)
   - `generated_at` timestamp fresh? (within expected pipeline SLA)

5. **Build coverage matrix** -> verify: every model x every applicable control class has a cell

   | Model | PK | FK | Fresh | Complete | Ranges | Dupes | Nulls | Recon |
   |-------|----|----|-------|----------|--------|-------|-------|-------|
   | ods_* | ?  | ?  | ?     | ?        | ?      | ?     | ?     | ?     |
   | dim_* | ?  | ?  | -     | ?        | ?      | ?     | ?     | -     |
   | dwd_* | ?  | ?  | ?     | ?        | ?      | ?     | ?     | ?     |
   | dws_* | ?  | -  | ?     | ?        | ?      | ?     | ?     | ?     |
   | ads_* | ?  | -  | -     | ?        | ?      | ?     | ?     | ?     |

   Legend: PASS / MISSING / N/A

   Applicability rules:
   - FK Integrity: required on DWD (facts reference dims), optional on DWS/ADS
   - Freshness: required on ODS and DWD, optional on aggregations
   - Business Reconciliation: required on at least one DWS or ADS model per mart

6. **Identify untested columns** -> verify: compare schema.yml column declarations against test coverage
   - List columns with no `not_null` or type test
   - Flag PK columns missing `unique` + `not_null`
   - Flag FK columns missing `relationships`

7. **Score and rank gaps** -> verify: output sorted by severity (error > warn)

   Severity assignment:
   - CRITICAL: PK Integrity missing on any model, FK Integrity missing on DWD, Freshness missing entirely
   - HIGH: Duplicate Detection missing on fact tables, Business Reconciliation missing entirely
   - MEDIUM: Null-Rate not configured, Completeness checks absent
   - LOW: Accepted Ranges missing on non-critical columns

## Output Checklist

- [ ] Coverage matrix table (model x control class) with PASS/MISSING/N/A
- [ ] Summary score: X/8 control classes fully covered
- [ ] Gap list sorted by severity (CRITICAL -> LOW)
- [ ] Untested columns list with recommended test type
- [ ] dqc_scorecard.json health status
- [ ] Remediation priority list (what to fix first)
- [ ] Overall verdict: PASS (all 8 covered) / PARTIAL (some gaps) / FAIL (critical gaps)

## Output Format

```
## DQC Audit Report -- {mart_name}

### Coverage Matrix
{table}

### Summary
- Control classes covered: X/8
- Models audited: N
- Tests found: M (G generic + S singular)
- Verdict: {PASS|PARTIAL|FAIL}

### Gaps (by severity)
1. [CRITICAL] {description} -- affects: {models}
2. [HIGH] {description} -- affects: {models}
...

### Untested Columns
- {model}.{column} -- recommended: {test_type}
...

### Remediation Priority
1. {action} -- resolves: {gap_ids}
...
```

## Resources

- `docs/dqc-framework.md` -- DQC control class catalog, scorecard format, quality gates
- Target mart's `schema.yml` files -- generic test inventory
- Target mart's `tests/` directory -- singular test inventory
- Target mart's `dqc_scorecard.json` -- reconciliation scorecard artifact
