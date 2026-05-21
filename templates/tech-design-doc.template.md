# Tech Design Document: {{ mart.name }}

> **Phase B artifact.** This document captures the physical design and column-level calculation specs for every model in the mart. It is produced after the Sign-Off PRD (Phase A) is approved and before any dbt model code is generated.
>
> Placeholders (`{{ ... }}`) must be replaced with real values from `mart.yml` and the approved PRD.

---

## Changelog

| Version | Date | Author | Summary |
|---------|------|--------|---------|
| 0.1 | {{ date }} | {{ author }} | Initial draft |

---

## 1. Design Reasoning (Kimball 4-Step)

### Step 1 — Select the business process

<!-- Which operational process does this mart model? Name the process, not the source system. -->

**Business process:** {{ business_process }}

**Source of data:** {{ providers.primary }}

### Step 2 — Declare the grain

<!-- What does one row represent? Be explicit: "one row per X per Y per Z." -->

**Grain statement:** {{ mart.grain }}

**Consequence:** Every column in the fact table must be true at this grain. If a metric requires a different grain, it belongs in a separate DWS model with its own grain declaration.

### Step 3 — Identify the dimensions

<!-- Dimensions answer the "who, what, where, when, how, why" of each fact row. -->

| Dimension | Conformed | SCD type | Source | Notes |
|-----------|-----------|----------|--------|-------|
| {{ prefix }}_dim_date | yes | Type 0 | seed | Role-playing date dimension |
| {{ dimension_2 }} | {{ conformed }} | {{ scd_type }} | {{ source }} | |

### Step 4 — Identify the facts

<!-- Facts are the numeric measurements of the business process. -->

| Fact / metric | Type | Unit | Formula summary |
|---------------|------|------|-----------------|
| {{ fact_1 }} | {{ additive / semi-additive / non-additive }} | {{ unit }} | {{ summary }} |

---

## 2. Bus Matrix

> Cross-reference business processes (rows) against dimensions (columns). Mark `X` where a process uses the dimension. See `docs/bus-matrix.md` for methodology.

| Business process | dim_date | {{ dim_2 }} | {{ dim_3 }} |
|------------------|----------|-------------|-------------|
| {{ process_1 }} | X | | |
| {{ process_2 }} | X | | |

---

## 3. Source-to-Target Mapping

> Trace every source field to its destination column. Each row answers: "Where does this data come from and what happens to it?"

### 3.1 ODS — {{ prefix }}_ods_{{ source }}_{{ entity }}

| Source field | Target column | Transform | Notes |
|-------------|---------------|-----------|-------|
| {{ source_field_1 }} | {{ target_column_1 }} | {{ transform_1 }} | |
| (computed) | provider | Literal `'{{ providers.primary }}'` | Provenance |
| (computed) | pull_ts_utc | `NOW()` | Provenance |
| {{ source_ts_field }} | quote_ts_utc | Pass-through | Provenance |
| (computed) | run_id | dbt var `run_id` | Provenance |

### 3.2 DIM — {{ prefix }}_dim_{{ entity }}

| Source column | Target column | Transform | Notes |
|---------------|---------------|-----------|-------|
| {{ dim_source_1 }} | {{ dim_target_1 }} | {{ dim_transform_1 }} | |

### 3.3 DWD — {{ prefix }}_dwd_{{ grain }}_{{ entity }}_di

| Source column (ODS/DIM) | Target column | Transform | Notes |
|-------------------------|---------------|-----------|-------|
| {{ dwd_source_1 }} | {{ dwd_target_1 }} | {{ dwd_transform_1 }} | |

### 3.4 DWS — {{ prefix }}_dws_{{ dimension }}_{{ metric }}_{{ window }}

| Source column (DWD/DWS) | Target column | Transform | Notes |
|-------------------------|---------------|-----------|-------|
| {{ dws_source_1 }} | {{ dws_target_1 }} | {{ dws_transform_1 }} | |

### 3.5 ADS — {{ prefix }}_ads_{{ consumer }}_{{ purpose }}

| Source column (DWS/DWD/DIM) | Target column | Transform | Notes |
|-----------------------------|---------------|-----------|-------|
| {{ ads_source_1 }} | {{ ads_target_1 }} | {{ ads_transform_1 }} | |

---

## 4. Physical Table Schemas

> Every column in every model must be documented. The `calculation` column contains the exact SQL expression or derivation logic — this is the core of the TDD.
>
> Abbreviations: PK = primary key, FK = foreign key, NK = natural key, DD = degenerate dimension, M = measure/metric, A = attribute, P = provenance.

### 4.1 ODS — {{ prefix }}_ods_{{ source }}_{{ entity }}

**Grain:** {{ ods_grain }}
**Materialization:** table
**Source:** {{ ods_source_description }}

| column_name | data_type | role | definition | example_value | calculation | data_source |
|-------------|-----------|------|------------|---------------|-------------|-------------|
| pull_date | DATE | PK | Date the data was pulled | 2026-05-21 | `CURRENT_DATE` | computed |
| {{ pk_col }} | {{ type }} | PK | {{ definition }} | {{ example }} | {{ calculation }} | {{ source }} |
| {{ column_3 }} | {{ type }} | {{ role }} | {{ definition }} | {{ example }} | {{ calculation }} | {{ source }} |
| provider | VARCHAR | P | Data provider identifier | cboe | Literal `'{{ providers.primary }}'` | computed |
| pull_ts_utc | TIMESTAMP | P | UTC timestamp of data pull | 2026-05-21T20:45:00Z | `NOW()` | computed |
| quote_ts_utc | TIMESTAMP | P | Source system timestamp | 2026-05-21T20:30:00Z | Pass-through from source | {{ providers.primary }} |
| run_id | VARCHAR | P | Pipeline execution ID | manual | `'{{ var("run_id", "manual") }}'` | dbt var |

### 4.2 DIM — {{ prefix }}_dim_{{ entity }}

**Grain:** {{ dim_grain }}
**Materialization:** table
**SCD type:** {{ scd_type }}

| column_name | data_type | role | definition | example_value | calculation | data_source |
|-------------|-----------|------|------------|---------------|-------------|-------------|
| {{ dim_sk }} | INTEGER | PK | Surrogate key | 20260521 | {{ sk_calculation }} | seed |
| {{ dim_nk }} | {{ type }} | NK | Natural key | {{ nk_example }} | {{ nk_calculation }} | seed |
| {{ dim_attr_1 }} | {{ type }} | A | {{ definition }} | {{ example }} | {{ calculation }} | seed |

> Unknown member row: ID = -1, all attributes = 'Unknown'.

### 4.3 DWD — {{ prefix }}_dwd_{{ grain }}_{{ entity }}_di

**Grain:** {{ dwd_grain }}
**Materialization:** table / incremental
**Source model:** {{ prefix }}_ods_{{ source }}_{{ entity }}
**Filter:** {{ dwd_filter_description }}

| column_name | data_type | role | definition | example_value | calculation | data_source |
|-------------|-----------|------|------------|---------------|-------------|-------------|
| {{ dwd_col_1 }} | {{ type }} | {{ role }} | {{ definition }} | {{ example }} | {{ calculation }} | {{ source_model }} |

### 4.4 DWS — {{ prefix }}_dws_{{ dimension }}_{{ metric }}_{{ window }}

**Grain:** {{ dws_grain }}
**Materialization:** table
**Source model:** {{ dwd_model_name }}
**Aggregation window:** {{ window }}

| column_name | data_type | role | definition | example_value | calculation | data_source |
|-------------|-----------|------|------------|---------------|-------------|-------------|
| {{ dws_col_1 }} | {{ type }} | {{ role }} | {{ definition }} | {{ example }} | {{ calculation }} | {{ source_model }} |

### 4.5 ADS — {{ prefix }}_ads_{{ consumer }}_{{ purpose }}

**Grain:** {{ ads_grain }}
**Materialization:** table / view
**Source models:** {{ ads_source_models }}

| column_name | data_type | role | definition | example_value | calculation | data_source |
|-------------|-----------|------|------------|---------------|-------------|-------------|
| {{ ads_col_1 }} | {{ type }} | {{ role }} | {{ definition }} | {{ example }} | {{ calculation }} | {{ source_model }} |

---

## 5. DQC Plan

> Map each DQC control class to the specific tests and thresholds for this mart. Reference `docs/dqc-framework.md` for the full control catalog.

### 5.1 Control coverage matrix

| Model | PK | FK | Fresh | Comp | Range | Dup | Null | Recon |
|-------|----|----|-------|------|-------|-----|------|-------|
| {{ prefix }}_ods_... | {{ status }} | {{ status }} | {{ status }} | {{ status }} | {{ status }} | {{ status }} | {{ status }} | {{ status }} |
| {{ prefix }}_dim_... | {{ status }} | {{ status }} | {{ status }} | {{ status }} | {{ status }} | {{ status }} | {{ status }} | {{ status }} |
| {{ prefix }}_dwd_... | {{ status }} | {{ status }} | {{ status }} | {{ status }} | {{ status }} | {{ status }} | {{ status }} | {{ status }} |
| {{ prefix }}_dws_... | {{ status }} | {{ status }} | {{ status }} | {{ status }} | {{ status }} | {{ status }} | {{ status }} | {{ status }} |
| {{ prefix }}_ads_... | {{ status }} | {{ status }} | {{ status }} | {{ status }} | {{ status }} | {{ status }} | {{ status }} | {{ status }} |

Legend: `G` = generic test (schema.yml), `S` = singular test (tests/), `N/A` = not applicable, `—` = gap (must justify).

### 5.2 Test specifications

| # | Control class | Test type | Test file / schema entry | Assertion | Tolerance | Severity |
|---|---------------|-----------|--------------------------|-----------|-----------|----------|
| 1 | PK Integrity | Generic | schema.yml: `not_null` + `unique` on {{ pk_columns }} | Zero violations | 0 | error |
| 2 | FK Integrity | Generic | schema.yml: `relationships` on {{ fk_columns }} | All FKs resolve | 0 | error |
| 3 | Freshness | Singular | tests/test_dqc_freshness.sql | {{ freshness_assertion }} | {{ tolerance }} | {{ severity }} |
| 4 | Completeness | Singular | tests/test_dqc_completeness.sql | {{ completeness_assertion }} | {{ tolerance }} | {{ severity }} |
| 5 | Accepted Ranges | Singular | tests/test_dqc_accepted_ranges.sql | {{ range_assertion }} | 0 | error |
| 6 | Duplicate Detection | Singular | tests/test_dqc_duplicate_detection.sql | {{ dup_assertion }} | 0 | error |
| 7 | Null-Rate | Singular | tests/test_dqc_null_rate.sql | {{ null_rate_assertion }} | {{ tolerance }} | {{ severity }} |
| 8 | Business Reconciliation | Singular | tests/test_dqc_reconciliation.sql | {{ recon_assertion }} | {{ tolerance }} | {{ severity }} |

---

## 6. Refresh Strategy

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Cron | `{{ schedule.cron }}` | {{ cron_rationale }} |
| Timezone | {{ schedule.timezone }} | {{ tz_rationale }} |
| Holiday handling | {{ schedule.skip_holidays }} | {{ holiday_rationale }} |
| Pipeline steps | {{ pipeline.steps }} | {{ steps_rationale }} |
| Fail-fast | {{ pipeline.fail_fast }} | {{ fail_fast_rationale }} |
| Timeout | {{ pipeline.timeout_minutes }} min | {{ timeout_rationale }} |

### Materialization strategy

| Model | Materialization | Strategy | Rationale |
|-------|----------------|----------|-----------|
| ODS | table | Full refresh | {{ ods_mat_rationale }} |
| DIM | table | Full refresh from seed | {{ dim_mat_rationale }} |
| DWD | table / incremental | {{ dwd_strategy }} | {{ dwd_mat_rationale }} |
| DWS | table | Full refresh | {{ dws_mat_rationale }} |
| ADS | table / view | {{ ads_strategy }} | {{ ads_mat_rationale }} |

### Dependency graph

```
seed (dim_date.csv)
  -> {{ prefix }}_dim_date
       -> {{ prefix }}_ads_*

{{ providers.primary }} API
  -> {{ prefix }}_ods_*
       -> {{ prefix }}_dwd_*
            -> {{ prefix }}_dws_*
                 -> {{ prefix }}_ads_*
```

---

## 7. Monitoring Plan

### Pipeline health

| Signal | Method | Threshold | Action |
|--------|--------|-----------|--------|
| Pipeline failure | GitHub Actions alert | Any step fails | Investigate logs, retry once |
| Runtime exceeded | Timeout setting | > {{ pipeline.timeout_minutes }} min | Check source API, scale resources |
| No data ingested | Completeness DQC | Row count = 0 | Check API availability, holiday calendar |

### Data quality

| Signal | Method | Threshold | Action |
|--------|--------|-----------|--------|
| DQC test failure | dbt test exit code | Any `error` severity fails | Pipeline halts (fail-fast), investigate |
| DQC warning | dbt test exit code | Any `warn` severity fails | Log, review in next business day |
| Null-rate spike | Null-rate singular test | > {{ dqc.null_rate_threshold }} | Check source data quality |
| Freshness breach | Freshness singular test | {{ dqc.freshness_threshold }} | Check source API lag |

### Scorecard artifact

Location: `{{ dqc.scorecard_artifact }}`

The DQC scorecard is updated after each pipeline run and tracks pass/fail/warn status for all 8 control classes. Review the scorecard weekly to identify trends and adjust thresholds.

---

## 8. Traceability Matrix

> Bidirectional mapping: every TDD metric traces forward to the SQL model and test that implements it, and every SQL expression traces back to the TDD section that specifies it.

### TDD field -> SQL model

| TDD section | Metric / column | Model file | SQL expression reference |
|-------------|-----------------|------------|--------------------------|
| 4.1 ODS | {{ column }} | models/ods/{{ ods_model }}.sql | Line {{ N }} |
| 4.3 DWD | {{ column }} | models/dwd/{{ dwd_model }}.sql | Line {{ N }} |
| 4.4 DWS | {{ column }} | models/dws/{{ dws_model }}.sql | Line {{ N }} |
| 4.5 ADS | {{ column }} | models/ads/{{ ads_model }}.sql | Line {{ N }} |

### SQL expression -> TDD field

| Model file | Column | TDD section | TDD column_name |
|------------|--------|-------------|-----------------|
| models/ods/{{ ods_model }}.sql | {{ column }} | 4.1 ODS | {{ tdd_column }} |
| models/dwd/{{ dwd_model }}.sql | {{ column }} | 4.3 DWD | {{ tdd_column }} |
| models/dws/{{ dws_model }}.sql | {{ column }} | 4.4 DWS | {{ tdd_column }} |
| models/ads/{{ ads_model }}.sql | {{ column }} | 4.5 ADS | {{ tdd_column }} |

---

## Sign-Off

This TDD must be approved before the `mart-bootstrap` skill proceeds to code generation (Phase B gate).

| Role | Name | Date | Status |
|------|------|------|--------|
| Tech lead / designer | {{ tdd_author }} | {{ date }} | pending |
| Reviewer | {{ reviewer }} | {{ date }} | pending |
