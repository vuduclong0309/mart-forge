# mart-review

Review a Kimball mart for production readiness with an adversarial posture.

## What it does

Comprehensive review covering:
1. **Naming conventions** -- all models follow `{prefix}_{layer}_{entity}` pattern
2. **Bus matrix coverage** -- fact tables reference all declared dimensions
3. **Grain declarations** -- every DWD has exactly one declared grain
4. **Incremental strategy** -- no idempotency violations (no current_timestamp, no SELECT *)
5. **Provenance columns** -- every ODS has provider, pull_ts_utc, quote_ts_utc, run_id
6. **Dimension lifecycle** -- SCD types declared, unknown member exists
7. **DQC audit** -- runs full dqc-audit as sub-check
8. **Pipeline config** -- GitHub Actions matches mart.yml

Outputs a graded scorecard (A/B/C/D/F) and a machine-readable `review_report.json` artifact for quality gate enforcement.

## Trigger phrases

- "review {mart} for production readiness"
- "is the mart ready to ship?"
- "run the reviewer agent checks on {mart}"
- "grade the warehouse quality"

## Grading

| Grade | Criteria |
|-------|----------|
| A | Zero Critical/High findings, all 8 DQC controls pass |
| B | Zero Critical, <=2 High, DQC >=6/8 |
| C | Zero Critical, <=4 High, DQC >=4/8 |
| D | <=1 Critical, multiple High, DQC partial |
| F | Multiple Critical, DQC absent |

## Prerequisites

- An existing mart with models, schema.yml, and optionally tests/pipeline

## References

- Naming conventions: `docs/naming-conventions.md`
- Bus matrix design: `docs/bus-matrix.md`
- DQC framework: `docs/dqc-framework.md`
- Agent orchestration: `docs/agent-orchestration.md`
