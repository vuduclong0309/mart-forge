# Data Quality Contract (DQC) Framework

Data Quality Contracts are the enforcement mechanism for data integrity in mart-forge. Every mart must implement all 8 control classes before it can pass the production readiness review.

## Table of Contents

- [Overview](#overview)
- [The 8 Control Classes](#the-8-control-classes)
- [Implementation in dbt](#implementation-in-dbt)
- [DQC Scorecard Artifact](#dqc-scorecard-artifact)
- [Quality Gates (G1-G5)](#quality-gates-g1-g5)
- [Applicability Matrix](#applicability-matrix)
- [Writing Custom Tests](#writing-custom-tests)

---

## Overview

A Data Quality Contract is a binding agreement that a mart's data meets defined correctness, completeness, and consistency criteria. Unlike ad-hoc tests, DQC controls are:

- **Mandatory** -- every mart must implement all 8 classes
- **Auditable** -- test results are recorded in `dqc_scorecard.json`
- **Gated** -- promotion through the pipeline requires all controls to pass
- **Versioned** -- the scorecard tracks when each control was last verified

### Where Tests Live

mart-forge uses two dbt test mechanisms:

1. **Generic tests** in `schema.yml` -- declarative column-level tests (`not_null`, `unique`, `relationships`, `accepted_values`)
2. **Singular tests** in `tests/` -- custom SQL queries that return rows on failure (freshness, completeness, null-rate, reconciliation, duplicate detection, accepted ranges)

Both count toward DQC coverage. The `dqc-audit` skill reads both sources when calculating the coverage matrix.

---

## The 8 Control Classes

### 1. PK Integrity

**What:** Every primary key is non-null and unique across all rows.

**Why:** Duplicate or null primary keys cause join fan-outs, incorrect aggregations, and downstream data corruption.

**Implementation:** Generic tests in `schema.yml`:

```yaml
# From examples/ecommerce-orders-mart/models/schema.yml
- name: ecom_dim_customer
  columns:
    - name: customer_sk
      tests:
        - not_null
        - unique
```

**Applies to:** Every model in every layer (ODS, DIM, DWD, DWS, ADS).

**Severity if missing:** CRITICAL

### 2. FK Integrity

**What:** Every foreign key in a fact table resolves to a valid row in the referenced dimension table, including the unknown member (sk = -1).

**Why:** Orphan foreign keys mean fact rows that cannot be analyzed by that dimension. Aggregations that join to dimensions will silently drop these rows.

**Implementation:** Generic `relationships` test in `schema.yml`:

```yaml
# From examples/ecommerce-orders-mart/models/schema.yml
- name: ecom_dwd_order_line_di
  columns:
    - name: customer_sk
      tests:
        - not_null
        - relationships:
            to: ref('ecom_dim_customer')
            field: customer_sk
    - name: product_sk
      tests:
        - not_null
        - relationships:
            to: ref('ecom_dim_product')
            field: product_sk
    - name: order_date_key
      tests:
        - not_null
        - relationships:
            to: ref('ecom_dim_date')
            field: date_key
```

**Applies to:** DWD (required), DWS (optional -- only if the model has direct FK columns).

**Severity if missing:** CRITICAL on DWD, MEDIUM on DWS.

### 3. Freshness

**What:** ODS data has been loaded recently. The `pull_ts_utc` column is populated and within the expected SLA window.

**Why:** Stale data leads to decisions based on outdated information. Freshness checks detect broken ingestion pipelines.

**Implementation:** Singular test in `tests/`:

```sql
-- From examples/ecommerce-orders-mart/tests/test_dqc_freshness.sql
select count(*) as stale_rows
from {{ ref('ecom_ods_raw_orders') }}
where pull_ts_utc is null
having count(*) > 0
```

For production marts with real data providers, the test should also check recency:

```sql
select count(*) as stale_rows
from {{ ref('ecom_ods_raw_orders') }}
where pull_ts_utc < current_timestamp - interval '24 hours'
having count(*) > 0
```

**Applies to:** ODS (required), DWD (recommended via inherited pull_ts_utc).

**Severity if missing:** CRITICAL

### 4. Completeness / Volume

**What:** Row counts meet minimum expected thresholds. The mart is not empty or suspiciously small.

**Why:** A pipeline that succeeds but produces zero rows is worse than one that fails loudly. Volume checks catch silent data loss.

**Implementation:** Singular test in `tests/`:

```sql
-- From examples/ecommerce-orders-mart/tests/test_dqc_completeness.sql
with checks as (
    select 'raw_orders' as model, count(*) as cnt, 500 as min_expected
    from {{ ref('ecom_ods_raw_orders') }}
    union all
    select 'dim_customer', count(*), 50
    from {{ ref('ecom_dim_customer') }}
    union all
    select 'dim_product', count(*), 20
    from {{ ref('ecom_dim_product') }}
    union all
    select 'fact_order_line', count(*), 500
    from {{ ref('ecom_dwd_order_line_di') }}
)
select model, cnt, min_expected
from checks
where cnt < min_expected
```

**Applies to:** All layers. Set thresholds based on business knowledge (how many orders do you expect per day?).

**Severity if missing:** MEDIUM

### 5. Accepted Ranges

**What:** Numeric values fall within plausible bounds. Enum columns contain only expected values.

**Why:** A negative quantity or a revenue value of $999,999,999 indicates data corruption or transformation bugs.

**Implementation:** Combination of generic tests (enums) and singular tests (numeric ranges):

```yaml
# Generic -- enum validation
- name: status
  tests:
    - accepted_values:
        values: ["complete", "pending", "cancelled", "refunded"]
```

```sql
-- Singular -- numeric range validation
-- From examples/ecommerce-orders-mart/tests/test_dqc_accepted_ranges.sql
select 'negative_quantity' as violation, count(*) as cnt
from {{ ref('ecom_dwd_order_line_di') }}
where quantity <= 0
having count(*) > 0

union all

select 'negative_unit_price', count(*)
from {{ ref('ecom_dwd_order_line_di') }}
where unit_price < 0
having count(*) > 0

union all

select 'negative_line_total', count(*)
from {{ ref('ecom_dwd_order_line_di') }}
where line_total < 0
having count(*) > 0
```

**Applies to:** DWD and DWS models with numeric measures or enum columns.

**Severity if missing:** LOW to MEDIUM depending on the column.

### 6. Duplicate Detection

**What:** No duplicate rows exist within the declared grain. Business key combinations are unique.

**Why:** Duplicates cause double-counting in aggregations. A duplicate order line inflates revenue.

**Implementation:** Singular test in `tests/`:

```sql
-- From examples/ecommerce-orders-mart/tests/test_dqc_duplicate_detection.sql
select
    order_id,
    line_id,
    count(*) as row_count
from {{ ref('ecom_dwd_order_line_di') }}
group by order_id, line_id
having count(*) > 1
```

**Applies to:** DWD (required -- grain enforcement), DWS (recommended), ADS (recommended).

**Severity if missing:** HIGH on DWD, MEDIUM on DWS/ADS.

### 7. Null-Rate Threshold

**What:** Non-PK columns do not exceed a configurable null percentage (default: 5%).

**Why:** High null rates indicate incomplete data loads or transformation bugs. A fact table where 50% of `line_total` is NULL is useless for revenue analysis.

**Implementation:** Singular test in `tests/`:

```sql
-- From examples/ecommerce-orders-mart/tests/test_dqc_null_rate.sql
with total as (
    select count(*) as total_rows from {{ ref('ecom_dwd_order_line_di') }}
),
null_checks as (
    select
        'quantity' as column_name,
        count(*) filter (where quantity is null) as null_count
    from {{ ref('ecom_dwd_order_line_di') }}
    union all
    select 'unit_price', count(*) filter (where unit_price is null)
    from {{ ref('ecom_dwd_order_line_di') }}
    union all
    select 'line_total', count(*) filter (where line_total is null)
    from {{ ref('ecom_dwd_order_line_di') }}
    union all
    select 'status', count(*) filter (where status is null)
    from {{ ref('ecom_dwd_order_line_di') }}
)
select nc.column_name, nc.null_count, t.total_rows,
    round(nc.null_count::double / t.total_rows, 4) as null_rate
from null_checks nc cross join total t
where nc.null_count::double / t.total_rows > 0.05
```

**Applies to:** DWD (required for measure columns), DWS (recommended).

**Severity if missing:** MEDIUM

### 8. Business Reconciliation

**What:** Mart totals match an external source of truth within a defined tolerance.

**Why:** Even if every individual test passes, the aggregate result could still be wrong (e.g., a join that silently drops rows). Reconciliation catches systemic errors that column-level tests miss.

**Implementation:** Singular test in `tests/`:

```sql
-- From examples/ecommerce-orders-mart/tests/test_dqc_reconciliation.sql
with seed_totals as (
    select
        sum(line_total) as seed_revenue,
        count(distinct order_id) as seed_order_count
    from {{ ref('raw_orders') }}
    where status != 'cancelled'
),
mart_totals as (
    select
        sum(line_total) as mart_revenue,
        count(distinct order_id) as mart_order_count
    from {{ ref('ecom_dwd_order_line_di') }}
    where status != 'cancelled'
)
select 'revenue_mismatch' as check_name,
    s.seed_revenue, m.mart_revenue,
    abs(s.seed_revenue - m.mart_revenue) as diff
from seed_totals s cross join mart_totals m
where abs(s.seed_revenue - m.mart_revenue) > 0.01

union all

select 'order_count_mismatch',
    s.seed_order_count, m.mart_order_count,
    abs(s.seed_order_count - m.mart_order_count)
from seed_totals s cross join mart_totals m
where s.seed_order_count != m.mart_order_count
```

**Configuration in mart.yml:**

```yaml
dqc:
  reconciliation:
    - metric: total_revenue
      source: raw_orders_seed
      tolerance: 0.01
      severity: error
    - metric: total_order_count
      source: raw_orders_seed
      tolerance: 0
      severity: error
```

**Applies to:** At least one DWS or ADS model per mart (required).

**Severity if missing:** HIGH

---

## Implementation in dbt

### Test Execution Order

dbt runs all tests after all models are built (`dbt build` = seed + run + test). The recommended pipeline order is:

```
dbt seed     # Load reference data (dim_date, raw CSVs)
dbt run      # Build all models (ODS -> DIM -> DWD -> DWS -> ADS)
dbt test     # Execute all generic + singular tests
```

### Test File Naming Convention

```
tests/
+-- test_dqc_freshness.sql
+-- test_dqc_completeness.sql
+-- test_dqc_accepted_ranges.sql
+-- test_dqc_duplicate_detection.sql
+-- test_dqc_null_rate.sql
+-- test_dqc_reconciliation.sql
```

Generic tests (PK integrity, FK integrity, accepted_values for enums) live in `schema.yml` and do not need separate test files.

### How Singular Tests Work

A singular test is a SQL query that returns zero rows on success. If any rows are returned, the test fails. This is a dbt convention:

```sql
-- Returns rows = FAIL; returns nothing = PASS
select order_id, line_id, count(*)
from {{ ref('ecom_dwd_order_line_di') }}
group by order_id, line_id
having count(*) > 1
```

---

## DQC Scorecard Artifact

The `dqc_scorecard.json` file is a machine-readable record of all 8 control classes and their pass/fail status. It is generated or updated after each test run.

### Schema

```json
{
  "mart": "ecommerce-orders-mart",
  "generated_at": "2026-05-16T09:00:00Z",
  "controls": [
    {
      "class": "pk_integrity",
      "description": "Primary keys are not null and unique",
      "models": ["ecom_dim_date", "ecom_dim_customer", "..."],
      "status": "pass",
      "verified_at": "2026-05-16T09:00:00Z"
    },
    {
      "class": "fk_integrity",
      "description": "All FKs resolve to dimension rows",
      "models": ["ecom_dwd_order_line_di"],
      "fk_checks": ["customer_sk -> ecom_dim_customer", "..."],
      "status": "pass",
      "verified_at": "2026-05-16T09:00:00Z"
    }
  ]
}
```

### Status Values

| Status | Meaning |
|--------|---------|
| `pass` | All tests for this control class succeeded |
| `fail` | One or more tests failed |
| `pending` | Tests exist but have not been run yet |
| `exhausted` | All available reconciliation sources attempted; proxy check in place (see Resource Exhaustion below) |

### Resource Exhaustion Loop

Before a control may be marked `exhausted`, the operator must demonstrate that **every plausible data source** has been attempted. The scorecard entry must include an `attempts[]` array documenting each attempt:

```json
{
  "attempts": [
    {
      "source": "Name of the data source or API",
      "result": "no_data | paywalled | error | pass",
      "reason": "Why this source could not satisfy the control",
      "date": "2026-05-18",
      "evidence_uri": "URL or file path to evidence"
    }
  ]
}
```

**Rules:**

1. `exhausted` is only valid when `attempts[]` contains at least **two** entries with `result` != `pass`, demonstrating that multiple sources were investigated.
2. At least one attempt must have `result: pass` -- the proxy or fallback reconciliation that is actually in place.
3. A bare waiver with zero investigation attempts is **not valid**. The old `unavailable` status has been retired.
4. The `waiver_signed_by` and `waiver_date` fields must accompany any `exhausted` entry to record who approved the resource exhaustion conclusion.

### dbt Test Linkage

Each scorecard entry carries two fields that mechanically link it to dbt test results:

- **`linked_dbt_tests`**: Array of dbt test `unique_id` strings (e.g. `test.gme_options_mart.test_dqc_freshness`) that contribute to this control class.
- **`last_dbt_run`**: ISO 8601 timestamp of the most recent `dbt test` invocation that updated this entry.

These fields are populated automatically by `scripts/dqc_update.py`, which reads `target/run_results.json` after each test run.

### Usage

- The `dqc-audit` skill reads this file to assess coverage
- The `mart-review` skill checks it as part of the production readiness grade
- CI pipelines parse it to enforce quality gates via `scripts/dqc_update.py`
- `scripts/dqc_update.py` exits non-zero if any control has `fail` status

---

## Quality Gates (G1-G5)

Quality gates are checkpoints in the mart lifecycle that require specific DQC controls to pass before the mart can advance.

### G1: Schema Validated

**When:** After `mart-bootstrap` generates the initial project structure.

**Requirements:**
- `mart.yml` is valid and parseable
- Directory structure matches convention
- All models have valid file names following naming conventions
- `dqc_scorecard.json` exists with all 8 classes in `pending` status

### G2: Models Build

**When:** After `dbt run` completes without errors.

**Requirements:**
- All ODS models populate without errors
- All DIM models populate with unknown member rows
- All DWD models populate with correct grain
- All DWS and ADS models populate
- No SQL compilation errors

### G3: DQC Pass

**When:** After `dbt test` completes.

**Requirements:**
- All 8 control classes have at least one test implemented
- All tests pass (zero failures)
- `dqc_scorecard.json` updated with `pass` status and current timestamp
- Reconciliation metrics match within declared tolerance

### G4: Review Approved

**When:** After `mart-review` runs its adversarial checks.

**Requirements:**
- Grade of B or higher (zero Critical findings, at most 2 High findings)
- Bus matrix coverage verified
- Grain declarations verified for every DWD
- No idempotency violations detected
- Provenance columns present on all ODS models

### G5: Production Ready

**When:** After human review and sign-off.

**Requirements:**
- G4 grade of A or B
- Pipeline schedule configured and tested
- Monitoring and alerting set up for freshness SLA
- Documentation complete (schema.yml descriptions, bus matrix)
- Stakeholder sign-off recorded

### Gate Progression

```
G1 (Schema) -> G2 (Build) -> G3 (DQC) -> G4 (Review) -> G5 (Production)
     |              |             |             |              |
  bootstrap       dbt run      dbt test    mart-review    human sign-off
```

A mart cannot skip gates. Failures at any gate block progression until resolved.

---

## Applicability Matrix

Not every control class applies to every layer. This matrix shows which controls are required, recommended, or not applicable per layer:

| Control Class | ODS | DIM | DWD | DWS | ADS |
|---|---|---|---|---|---|
| PK Integrity | Required | Required | Required | Required | Required |
| FK Integrity | N/A | N/A | **Required** | Optional | N/A |
| Freshness | **Required** | N/A | Recommended | N/A | N/A |
| Completeness | Recommended | Recommended | **Required** | Recommended | Recommended |
| Accepted Ranges | Optional | Optional | **Required** | Recommended | Optional |
| Duplicate Detection | Optional | Optional | **Required** | Recommended | Recommended |
| Null-Rate | Optional | Optional | **Required** | Recommended | Optional |
| Reconciliation | N/A | N/A | Optional | **Required** (1+) | Optional |

**Legend:**
- **Required** -- Must implement. Missing = CRITICAL or HIGH finding in review.
- Recommended -- Should implement. Missing = MEDIUM finding.
- Optional -- Nice to have. Missing = LOW finding.
- N/A -- Not applicable to this layer.

---

## Writing Custom Tests

### Template for a New Singular Test

```sql
-- DQC Control: {control_class_name}
-- Description: {what this test verifies}
-- Severity: {error|warn}

select '{violation_name}' as violation, count(*) as cnt
from {{ ref('{model_name}') }}
where {condition_that_identifies_bad_rows}
having count(*) > 0
```

### Combining Multiple Checks

Use `UNION ALL` to combine multiple checks into a single test file:

```sql
select 'check_a' as violation, count(*) as cnt
from {{ ref('model') }}
where condition_a
having count(*) > 0

union all

select 'check_b', count(*)
from {{ ref('model') }}
where condition_b
having count(*) > 0
```

### Parameterizing Thresholds

Use dbt variables for configurable thresholds:

```sql
{% set null_threshold = var('dqc_null_threshold', 0.05) %}

select column_name, null_rate
from (
    select 'quantity' as column_name,
        count(*) filter (where quantity is null)::double / count(*) as null_rate
    from {{ ref('model') }}
)
where null_rate > {{ null_threshold }}
```

---

## Checklist for New Marts

- [ ] All 8 control classes implemented (at least one test per class)
- [ ] `dqc_scorecard.json` present with all 8 classes listed
- [ ] Generic tests in `schema.yml`: PK (`not_null` + `unique`), FK (`relationships`), enums (`accepted_values`)
- [ ] Singular tests in `tests/`: freshness, completeness, ranges, duplicates, null-rate, reconciliation
- [ ] Reconciliation metrics defined in `mart.yml` with tolerance and severity
- [ ] All tests pass (`dbt test` exits 0)
- [ ] Scorecard updated with `pass` status and timestamps
