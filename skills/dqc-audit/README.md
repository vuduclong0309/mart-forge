# dqc-audit

Audit Data Quality Contract coverage for a Kimball mart against the 8 required control classes.

## What it does

Validates that a mart implements all 8 DQC control classes:
1. PK Integrity (not_null + unique on every PK)
2. FK Integrity (relationships to each DIM)
3. Freshness (pull_ts_utc within SLA)
4. Completeness / Volume (row count vs prior run)
5. Accepted Ranges (enum validation, numeric bounds)
6. Duplicate Detection (business key uniqueness)
7. Null-Rate Threshold (configurable null percentage)
8. Business Reconciliation (external source comparison)

Outputs a coverage matrix, gap list ranked by severity, untested columns, and an overall verdict (PASS/PARTIAL/FAIL).

## Trigger phrases

- "audit DQC coverage for {mart}"
- "check test coverage on the warehouse"
- "what DQC controls are missing?"
- "validate quality gates for {mart}"

## Prerequisites

- An existing mart with models and optionally schema.yml/tests
- `dqc_scorecard.json` (checked if present, absence is flagged)

## References

- DQC specification: `docs/dqc-framework.md`
- Reference implementation: `examples/ecommerce-orders-mart/`
