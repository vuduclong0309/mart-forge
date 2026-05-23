---
name: source-discovery
description: |
  Enumerate and vet candidate data sources from a WIKI-like stakeholder document or domain description.
  Records availability, auth requirements, license/terms, freshness, and schema shape for each source.
  Separates public-accessible metrics from those requiring private credentials or approval.
  Produces a structured source catalog that feeds directly into the BRD (Section 4) and mart.yml.

  **Use when:**
  - User provides a wiki page, stakeholder brief, or domain description and wants to know "what data can I actually get?"
  - Starting a new mart from a WIKI-like document (pre-BRD step)
  - "what sources are available for {domain}?"
  - "can I actually get this data?"
  - "which of these metrics require private API keys?"
  - BRD Section 4 has many [ASSUMED] tags — run this to upgrade them to [CONFIRMED]

  **Not for:**
  - Writing the BRD (use mart-brd after source discovery is complete)
  - Designing physical schemas (use mart-tdd after BRD sign-off)
  - Scaffolding models (use mart-bootstrap after TDD sign-off)
---

# Source Discovery

Reads a WIKI-like stakeholder document or domain description and produces a vetted source catalog
enumerating candidate data sources with availability, auth, license, freshness, and schema details.
The catalog output feeds directly into `mart-brd` Section 4 and `mart.yml` providers.

## Position in the Lifecycle

Source discovery is a pre-BRD step (Phase A0). It is optional but strongly recommended when the
user starts from a narrative document rather than a known data pipeline.

```
[A0] Source Discovery → [A] BRD → approval → [B] TDD → approval → [C] Scaffold → [D] DQC → [E] Dashboard
```

Running source discovery before the BRD ensures that:
- BRD Section 4 sources are tagged [CONFIRMED] rather than [ASSUMED]
- Metrics that require unavailable data are flagged before design work begins
- Public vs private access boundaries are drawn explicitly

## Constraints (read before doing anything)

- **Do not fabricate availability** — if you cannot verify that a source is accessible, tag it [UNVERIFIED] and
  document what check would confirm it.
- **Distinguish public vs private** — public sources (no auth required, no license fee) are tagged [PUBLIC].
  Sources requiring an API key, subscription, or data-sharing agreement are tagged [PRIVATE].
- **Record the schema shape, not invented columns** — list what fields the source actually provides based on
  documentation or sample data. Do not invent column names.
- **License and terms matter** — for any source used in a public mart, note whether redistribution of
  derived data is permitted by the provider's terms.
- **Freshness is a gate** — if a metric requires intraday freshness but the only available source updates
  daily, record this mismatch explicitly. The BRD cadence section must reconcile it.
- **One row per source, not per metric** — multiple metrics may share a source. Catalog the source once;
  map metrics to it in the BRD.

## Workflow

### Step 1 — Parse stakeholder input

Accept any of the following as input:
- A wiki page or markdown document describing the domain
- A list of desired metrics or KPIs
- A verbal description of the business process
- An existing BRD with [ASSUMED] sources to upgrade

Extract:
- The domain/business process being measured
- All metrics and dimensions mentioned (even informally)
- Any source names, URLs, or provider names mentioned
- Any constraints mentioned (latency, cost, licensing)

If no input is provided, ask the user: "What domain or business process are you trying to measure?
What data do you need to support it?"

### Step 2 — Enumerate candidate sources

For each metric or dimension identified in Step 1:

1. Identify which data source(s) could provide it
2. For each candidate source, record:
   - **Name**: provider name and specific endpoint/feed
   - **URL**: public documentation or landing page (if known)
   - **Type**: API / file download / database / scrape / manual upload
   - **Auth**: None / API key / OAuth / subscription / data-sharing agreement
   - **License**: terms for derived data use and redistribution
   - **Freshness**: update cadence (real-time / intraday / daily / weekly / manual)
   - **Schema**: known fields relevant to the target metrics (from docs or sample)
   - **Availability**: [PUBLIC] / [PRIVATE] / [UNVERIFIED]
   - **Metrics covered**: which metrics from Step 1 this source satisfies

### Step 3 — Verify availability

For each [UNVERIFIED] source, attempt to verify:
- Does the documentation URL resolve?
- Is the endpoint reachable without auth?
- Does a sample payload confirm the expected schema?

Update tags:
- [CONFIRMED] — access verified, schema matches expectations
- [UNVERIFIED] — could not confirm; document what check failed or is pending
- [UNAVAILABLE] — source explicitly requires access that cannot be obtained (e.g. paid subscription,
  NDA, or deprecated API)

### Step 4 — Classify public vs private metrics

After cataloging all sources, classify each metric as:

| Class | Meaning |
|-------|---------|
| **PUBLIC** | All required sources are [CONFIRMED] with no auth or with freely available credentials |
| **PRIVATE** | At least one required source is [PRIVATE] or requires a paid subscription |
| **UNVERIFIED** | At least one required source is [UNVERIFIED] — BRD may use it but must note the risk |
| **UNSUPPORTED** | No viable source found; metric cannot be built with available data |

### Step 5 — Identify schema gaps

For each confirmed source, note:
- Fields that are present but need transformation (type cast, rename, normalize)
- Fields that are missing from the source but required for a metric (mark as derivable or gap)
- Fields with known quality issues (nulls, stale values, inconsistent formats)

### Step 6 — Produce the source catalog

Output a structured source catalog with these sections:

```markdown
## Source Catalog

### Sources

| Source | Type | Auth | Freshness | Availability | Metrics Covered |
|--------|------|------|-----------|-------------|-----------------|
| {name} | {type} | {auth} | {freshness} | [CONFIRMED/PRIVATE/UNVERIFIED] | {metric list} |

### Source Details

For each source:
- **Endpoint / URL**: ...
- **License / Terms**: ...
- **Key fields**: ...
- **Known issues**: ...

### Metric Availability Summary

| Metric | Class | Source(s) | Notes |
|--------|-------|-----------|-------|
| {metric} | PUBLIC/PRIVATE/UNVERIFIED/UNSUPPORTED | {source list} | ... |

### Open Items

- [ ] {items that need manual verification or access requests}
```

### Step 7 — STOP and present findings

Present a summary to the user:
- How many sources found (confirmed / private / unverified / unavailable)
- How many metrics are PUBLIC vs PRIVATE vs UNSUPPORTED
- Open items requiring manual verification or access requests
- Recommendation: proceed to BRD, or resolve blockers first?

Ask: "Shall I proceed to `/mart-brd` using this source catalog, or do you want to resolve the
open items first?"

Do NOT auto-proceed to the BRD. The user must explicitly approve.

## Output Checklist

- [ ] All metrics from stakeholder input are classified (PUBLIC / PRIVATE / UNVERIFIED / UNSUPPORTED)
- [ ] Every source has Name, Type, Auth, Freshness, License, Availability tag
- [ ] Schema fields documented for each [CONFIRMED] source
- [ ] Schema gaps and quality issues noted
- [ ] Open items listed for unverified sources
- [ ] No fabricated URLs or invented schema fields
- [ ] No confidential data — use generic provider names for examples

## Handoff to BRD

When the user approves proceeding, pass the source catalog to `/mart-brd` as the Section 4 input.
The BRD skill will:
- Copy confirmed sources into Section 4 with [CONFIRMED] tags
- Copy unverified sources with [ASSUMED] tags and note the open item
- Use the metric availability classification to flag UNSUPPORTED metrics as TBD in Section 2

## Resources

- `docs/provider-abstraction.md` — Provider abstraction patterns for mart.yml
- `templates/mart.yml.template` — mart.yml providers schema for recording source metadata
- `skills/mart-brd/SKILL.md` — BRD Section 4 format (sources output feeds directly here)
