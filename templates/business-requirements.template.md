# Business Requirements Document: {{ mart.name }}

> **Phase A artifact.** Fill every section before proceeding to TDD (Phase B).
> Placeholders (`{{ ... }}`) must be replaced with real values from the client input.
> The operator must sign off on this BRD before any technical design begins.

---

## 1. Business Process

**Mart name:** {{ mart.name }}
**Business process:** {{ business_process.name }}

### Process description

<!-- What business activity does this mart measure? Describe the operational process end-to-end. -->

### Business questions this mart answers

<!-- List the 3-5 key questions stakeholders need answered. Be specific. -->

1. {{ business_question_1 }}
2. {{ business_question_2 }}
3. {{ business_question_3 }}

### Scope boundaries

<!-- What is explicitly IN scope and OUT of scope for this mart? -->

| Boundary | In scope | Out of scope |
|----------|----------|--------------|
| Time range | {{ scope.time_range }} | |
| Entities | {{ scope.entities }} | |
| Geographies | {{ scope.geographies }} | |

---

## 2. Metrics Catalog

Every metric the mart must produce. Each entry becomes a DWS/ADS column with a traceable calculation spec in the TDD.

| # | Metric name | Business definition | Unit | Grain | Aggregation | Priority |
|---|-------------|---------------------|------|-------|-------------|----------|
| M1 | {{ metric_1.name }} | {{ metric_1.definition }} | {{ metric_1.unit }} | {{ metric_1.grain }} | {{ metric_1.aggregation }} | must-have / nice-to-have |
| M2 | {{ metric_2.name }} | {{ metric_2.definition }} | {{ metric_2.unit }} | {{ metric_2.grain }} | {{ metric_2.aggregation }} | must-have / nice-to-have |

**Metric naming rules:**
- Use `snake_case`, no abbreviations without glossary entry
- Include unit in the name when ambiguous (e.g. `revenue_usd`, `duration_seconds`)
- Prefix derived metrics with their aggregation window (e.g. `daily_order_count`, `mtd_revenue`)

---

## 3. Domain Glossary

Define every domain-specific term used in this BRD. Ambiguous terms cause incorrect grain, wrong joins, and mismatched expectations between builder and consumer.

| Term | Definition | Example | Aliases to avoid |
|------|------------|---------|------------------|
| {{ term_1 }} | {{ definition_1 }} | {{ example_1 }} | {{ aliases_1 }} |
| {{ term_2 }} | {{ definition_2 }} | {{ example_2 }} | {{ aliases_2 }} |

**Glossary rules:**
- Every entity in the grain declaration must have a glossary entry
- Every dimension name must have a glossary entry
- If two stakeholders use different names for the same concept, pick one and list the other as "alias to avoid"

---

## 4. Data Sources

| # | Source name | Type | Format | Auth | Freshness | Volume estimate | Notes |
|---|------------|------|--------|------|-----------|-----------------|-------|
| S1 | {{ source_1.name }} | API / DB / file / seed | {{ source_1.format }} | {{ source_1.auth }} | {{ source_1.freshness }} | {{ source_1.volume }} | |
| S2 | {{ source_2.name }} | API / DB / file / seed | {{ source_2.format }} | {{ source_2.auth }} | {{ source_2.freshness }} | {{ source_2.volume }} | |

### Source-to-entity mapping

<!-- Which source feeds which business entity? This becomes the ODS layer design in the TDD. -->

| Source | Entities provided | Key fields | Known quality issues |
|--------|-------------------|------------|----------------------|
| {{ source_1.name }} | {{ source_1.entities }} | {{ source_1.keys }} | {{ source_1.quality_issues }} |

### Data access prerequisites

<!-- List credentials, VPN access, API keys, rate limits, or approval processes needed before the builder can proceed. -->

- [ ] {{ prerequisite_1 }}
- [ ] {{ prerequisite_2 }}

---

## 5. Stakeholder Needs

### Consumer personas

| Persona | Role | Key questions they ask | Delivery format | Refresh expectation |
|---------|------|------------------------|-----------------|---------------------|
| {{ persona_1.name }} | {{ persona_1.role }} | {{ persona_1.questions }} | dashboard / SQL / export | {{ persona_1.refresh }} |
| {{ persona_2.name }} | {{ persona_2.role }} | {{ persona_2.questions }} | dashboard / SQL / export | {{ persona_2.refresh }} |

### Acceptance criteria

The mart is considered complete when all of the following are true:

- [ ] All must-have metrics from Section 2 are queryable
- [ ] Data freshness meets the SLA in Section 6
- [ ] DQC scorecard shows PASS on all 8 control classes
- [ ] Each consumer persona can answer their key questions using the ADS layer
- [ ] {{ additional_acceptance_criterion }}

### Data sensitivity

| Field / column pattern | Classification | Handling |
|------------------------|---------------|----------|
| {{ field_1 }} | public / internal / restricted | {{ handling_1 }} |

**Classification definitions:**
- **Public** -- safe for external sharing, no PII, no trade secrets
- **Internal** -- visible to authenticated workspace members only
- **Restricted** -- PII, financial positions, credentials, or regulatory data; must be masked, encrypted, or access-controlled

---

## 6. Cadence & Refresh

| Parameter | Value |
|-----------|-------|
| Refresh frequency | {{ cadence.frequency }} |
| Cron expression | `{{ cadence.cron }}` |
| Timezone | {{ cadence.timezone }} |
| SLA (data available by) | {{ cadence.sla }} |
| Holiday handling | skip / backfill / {{ cadence.holiday_policy }} |
| Historical backfill | {{ cadence.backfill_range }} |
| Expected pipeline duration | {{ cadence.pipeline_duration }} |

### Lifecycle expectations

- **Retention:** How long should historical data be kept? {{ cadence.retention }}
- **Deprecation:** Under what conditions would this mart be retired? {{ cadence.deprecation_trigger }}

---

## 7. Sign-Off

Both lines must be completed before Phase B (TDD) can begin. The `mart-brd` skill enforces this gate.

| Role | Name | Date | Status |
|------|------|------|--------|
| Operator (data owner) | {{ sign_off.operator.name }} | {{ sign_off.operator.date }} | pending / approved / approved-with-conditions / rejected |
| Consumer (primary user) | {{ sign_off.consumer.name }} | {{ sign_off.consumer.date }} | pending / approved / approved-with-conditions / rejected |

**Solo-operator exception:** If the operator is also the sole consumer, they may self-sign both lines. Document the reason:

> {{ sign_off.solo_operator_note }}

**Conditions (if approved-with-conditions):**

> {{ sign_off.conditions }}
