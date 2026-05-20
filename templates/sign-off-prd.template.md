# Sign-Off PRD: {{ mart.name }}

> Generated from `mart.yml`. Fill every section before sign-off.
> Placeholders (`{{ ... }}`) must be replaced with real values.

---

## 1. Business Purpose

**Mart name:** {{ mart.name }}
**Version:** {{ mart.version }}

### Why this mart exists

<!-- Describe the business problem this mart solves -->

### Stakeholder problem

<!-- What question or pain point does the primary stakeholder need addressed? -->

### Consumer personas

| Persona | Role | How they use this mart |
|---------|------|------------------------|
| {{ consumer_persona_1 }} | {{ role_1 }} | {{ usage_1 }} |

---

## 2. Source Systems

| Provider | Auth required | Rate limits | Freshness SLA |
|----------|---------------|-------------|---------------|
| {{ providers.primary }} | {{ providers.auth_required }} | {{ providers.rate_limit }} | {{ providers.freshness_sla }} |
| {{ providers.fallback }} | {{ providers.fallback_auth_required }} | {{ providers.fallback_rate_limit }} | {{ providers.fallback_freshness_sla }} |

**Notes:**
- Remove the fallback row if `providers.fallback` is null.
- Document any API pagination, throttle, or retry behavior relevant to SLA.

---

## 3. Grain & Dimensions

### Fact grain

**Primary grain:** {{ mart.grain }}

### Bus matrix

| Dimension | Conformed | SCD type | Notes |
|-----------|-----------|----------|-------|
| {{ dimension_1 }} | yes / no | Type 1 / Type 2 | |

### Conformed dimensions

List dimensions shared with other marts (from `dimensions.conformed` in `mart.yml`):

- {{ dimensions.conformed[] }}

### Local dimensions

Dimensions scoped to this mart only (from `dimensions.local` in `mart.yml`):

- {{ dimensions.local[] }}

---

## 4. Refresh Cadence

| Parameter | Value |
|-----------|-------|
| Cron expression | `{{ schedule.cron }}` |
| Timezone | {{ schedule.timezone }} |
| Holiday handling | {{ schedule.skip_holidays }} |
| Pipeline steps | {{ pipeline.steps }} |
| Fail-fast | {{ pipeline.fail_fast }} |
| Timeout (minutes) | {{ pipeline.timeout_minutes }} |

**Holiday policy:** If `skip_holidays` is true, document which holiday calendar is used and how missed runs are back-filled.

---

## 5. DQC Controls

All 8 DQC control classes must be addressed. For each class, specify the metric under test, the tolerance threshold, and the severity level.

| # | Control class | Metric / test description | Tolerance | Severity |
|---|---------------|--------------------------|-----------|----------|
| 1 | PK Integrity | `not_null` + `unique` on every primary key | 0 | error |
| 2 | FK Integrity | `relationships` test for every foreign key | 0 | error |
| 3 | Freshness | Max age of `pull_ts_utc` vs wall clock | {{ dqc.freshness_threshold }} | {{ dqc.freshness_severity }} |
| 4 | Completeness | Row count vs prior run delta | {{ dqc.completeness_threshold }} | {{ dqc.completeness_severity }} |
| 5 | Accepted Ranges | `accepted_values` for enums, range tests for numerics | 0 | error |
| 6 | Duplicate Detection | Business key uniqueness within grain window | 0 | error |
| 7 | Null-Rate | Null percentage thresholds per column | {{ dqc.null_rate_threshold }} | {{ dqc.null_rate_severity }} |
| 8 | Business Reconciliation | {{ dqc.reconciliation.metric }} vs {{ dqc.reconciliation.source }} | {{ dqc.reconciliation.tolerance }} | {{ dqc.reconciliation.severity }} |

**Scorecard artifact:** `{{ dqc.scorecard_artifact }}`
**Control catalog enforcement:** {{ dqc.control_catalog }}

---

## 6. Data Sensitivity

Classify every field that enters or exits this mart.

| Field / column pattern | Classification | Handling |
|------------------------|---------------|----------|
| {{ field_1 }} | public / internal / restricted | {{ handling_1 }} |

**Classification definitions:**
- **Public** — safe for external sharing, no PII, no trade secrets.
- **Internal** — visible to authenticated workspace members only.
- **Restricted** — PII, financial positions, credentials, or data subject to regulatory constraints. Must be masked, encrypted, or access-controlled.

---

## 7. Sign-Off Block

Both lines must be completed before the mart-bootstrap skill proceeds past Phase A.

| Role | Name | Title / responsibility | Date | Status |
|------|------|-----------------------|------|--------|
| Operator (stakeholder) | {{ sign_off.operator.name }} | {{ sign_off.operator.role }} | {{ sign_off.operator.date }} | approved / approved-with-conditions / rejected |
| Customer / consumer | {{ sign_off.consumer.name }} | {{ sign_off.consumer.role }} | {{ sign_off.consumer.date }} | approved / approved-with-conditions / rejected |

**Solo-operator exception:** If the operator is also the sole consumer, they may self-sign both lines. Document the reason below:

> {{ sign_off.solo_operator_note }}

**Conditions (if approved-with-conditions):**

> {{ sign_off.conditions }}
