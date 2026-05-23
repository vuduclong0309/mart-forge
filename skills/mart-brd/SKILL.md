---
name: mart-brd
description: |
  Produce a Business Requirements Document (BRD) for a new Kimball mart. Extracts business process, metrics catalog, domain glossary, data sources, stakeholder needs, and cadence from client input. Outputs a structured BRD from the template for operator sign-off.

  **HARD GATE: No TDD (Phase B) until the BRD is signed off.** The agent must STOP after producing the BRD and wait for operator approval before any technical design, schema work, or scaffolding begins.

  **Use when:**
  - "create a BRD for {domain/source}"
  - "write business requirements for a new mart"
  - "Phase A for {domain}"
  - "what metrics should this mart have?"
  - User provides a case study, data file, verbal description, WIKI document, or existing docs and wants a structured requirements document
  - Source catalog from `/source-discovery` is ready and the user wants to formalize requirements

  **Not for:**
  - Vetting whether a data source is accessible — run `/source-discovery` first if sources are unknown
  - Writing the TDD / technical design (use mart-tdd after BRD sign-off)
  - Scaffolding models (use mart-bootstrap Phase B after TDD sign-off)
  - Reviewing an existing mart (use mart-review)
  - Auditing DQC coverage (use dqc-audit)
---

# Mart BRD

Reads client input (case study, data file, verbal description, WIKI document, or existing documentation)
and produces a structured Business Requirements Document using `templates/business-requirements.template.md`.
The BRD captures the domain model in business terms before any technical design begins.

## HARD GATE

**No TDD until BRD is signed off.** This is non-negotiable.

The lifecycle is:

```
[A0] Source Discovery (optional)  -->  [Phase A] BRD  -->  sign-off  -->  [Phase B] TDD  -->  ...
```

Phase B (`mart-bootstrap`) cannot begin until both sign-off lines in BRD Section 7 have status
`approved` or `approved-with-conditions`. If the operator has not signed off, STOP and remind them.
Do not proceed to technical design, schema work, `mart.yml` creation, or scaffolding.

## Source Discovery Pre-Step

If the user is starting from a WIKI-like document and data sources are not already vetted, run
`/source-discovery` before this skill. Source discovery produces a structured catalog that populates
BRD Section 4 with [CONFIRMED] tags rather than [ASSUMED] guesses. The key handoff is:

- `/source-discovery` output → Section 4 (Data Sources) of the BRD
- Metric availability classes (PUBLIC / PRIVATE / UNVERIFIED / UNSUPPORTED) → Section 2 annotations
- Open items from source discovery → Section 7 open TBDs

If a source catalog is provided, use it directly in Step 5 below. Skip any source research that
the catalog already covers.

## Constraints (read before doing anything)

- **Business language only** -- the BRD uses stakeholder terminology, not SQL column names or dbt model names. Technical mapping happens in the TDD.
- **Every metric must be defined** -- no vague aggregations like "total sales." Specify: name, business definition, unit, grain, aggregation method.
- **Every domain term must be glossaried** -- if two people could interpret a term differently, it needs a glossary entry.
- **Source-tag information provenance** -- mark each data source as [CONFIRMED] (verified access exists) or [ASSUMED] (inferred from client input, needs verification).
- **'I don't know yet' is valid** -- if the client input is insufficient to fill a section, mark it as `{{ TBD -- needs: <what's missing> }}` rather than fabricating requirements.
- **Never auto-approve** -- the sign-off section must always start with status `pending`. Only the operator can change it.

## Workflow

1. **Gather client input** -> verify: at least one of the following exists
   - Case study document or brief
   - Sample data file (CSV, JSON, API response)
   - Verbal description from the stakeholder
   - Existing documentation or wiki pages
   - Source catalog produced by `/source-discovery`

   If no input is provided, ask the operator what business process the mart should measure. Do not proceed with zero input.

   If starting from WIKI-like input without a source catalog, recommend running `/source-discovery`
   first so that Section 4 sources are verified rather than assumed.

2. **Identify the business process** -> verify: can be stated in one sentence
   - What operational activity does this mart measure?
   - What is the verb? (orders, trades, visits, shipments, registrations)
   - What is the grain? (per order line, per trade execution, per session)
   - What are the scope boundaries? (time range, entities, geographies)

3. **Extract metrics** -> verify: each metric has all 6 fields filled
   - Scan client input for quantitative questions ("how many", "what's the total", "average", "rate of")
   - For each metric, define: name, business definition, unit, grain, aggregation method
   - Classify as must-have or nice-to-have
   - If a source catalog is available, annotate each metric with its availability class
     (PUBLIC / PRIVATE / UNVERIFIED / UNSUPPORTED)
   - Flag UNSUPPORTED metrics as `{{ TBD -- no viable source found }}` in Section 2
   - Flag metrics that require calculation specs (these become TDD column-level specs in Phase B)

4. **Build domain glossary** -> verify: every entity and dimension term is defined
   - Extract all domain-specific nouns from client input
   - Define each term unambiguously
   - Identify aliases and pick a canonical name
   - Ensure every entity in the grain declaration has a glossary entry

5. **Catalog data sources** -> verify: each source has type, format, auth, freshness, volume
   - If a `/source-discovery` catalog is available, import it directly here. Each source already has
     Type, Auth, Freshness, License, Availability, and schema fields — copy them as-is and preserve
     the [CONFIRMED] / [PRIVATE] / [UNVERIFIED] tags.
   - For any source NOT in the discovery catalog, or if no catalog was produced:
     - List every data source referenced in client input
     - Map sources to business entities they provide
     - Identify key fields for each source
     - Note known quality issues (nulls, duplicates, late-arriving data)
     - Tag each as [CONFIRMED] or [ASSUMED]
     - List data access prerequisites (credentials, approvals, VPN)

   Source table format:

   | Source | Type | Auth | Freshness | Availability | Metrics Covered |
   |--------|------|------|-----------|-------------|-----------------|
   | {name} | {type} | {auth} | {cadence} | [CONFIRMED/PRIVATE/ASSUMED] | {metric list} |

6. **Define stakeholder needs** -> verify: at least one consumer persona with delivery expectations
   - Identify consumer personas (who queries this mart?)
   - Document their key questions and delivery format preferences
   - Write acceptance criteria: what makes this mart "done"?
   - Classify data sensitivity (public / internal / restricted)

7. **Define cadence** -> verify: refresh frequency, SLA, and lifecycle expectations are stated
   - Determine refresh frequency from stakeholder needs and source freshness
   - If source freshness caps latency below the desired SLA, document the mismatch explicitly
   - Set the SLA (when must data be available after refresh?)
   - Document holiday handling and backfill requirements
   - State retention and deprecation expectations

8. **Produce the BRD** -> verify: all 7 sections filled, sign-off block has status `pending`
   - Copy `templates/business-requirements.template.md`
   - Replace all placeholders with extracted values
   - Mark unresolvable placeholders as `{{ TBD -- needs: <what's missing> }}`
   - Set both sign-off statuses to `pending`

9. **STOP** -> inform the operator that the BRD is ready for review
   - Present a summary: business process, metric count (must-have vs nice-to-have), source count, open TBDs
   - Ask the operator to review and sign off before Phase B begins
   - Do NOT proceed to TDD, mart.yml, or any scaffolding

## Output Checklist

- [ ] Section 1: Business process identified with scope boundaries
- [ ] Section 2: Metrics catalog with all 6 fields per metric; UNSUPPORTED metrics flagged as TBD
- [ ] Section 3: Domain glossary with no ambiguous terms
- [ ] Section 4: Data sources cataloged with provenance tags ([CONFIRMED] / [PRIVATE] / [ASSUMED])
- [ ] Section 5: Stakeholder personas and acceptance criteria defined
- [ ] Section 6: Cadence, SLA, and lifecycle expectations stated; freshness mismatches documented
- [ ] Section 7: Sign-off block with both lines set to `pending`
- [ ] All unresolvable fields marked as `{{ TBD }}` with explanation
- [ ] No technical design (column names, SQL, model names) in the BRD
- [ ] BRD saved to `{mart_name}/business-requirements.md`

## Traceability

After BRD sign-off, the TDD must demonstrate bidirectional traceability:

- **Forward:** Every metric in BRD Section 2 maps to at least one DWS/ADS column in the TDD
- **Backward:** Every DWS/ADS column in the TDD traces back to a BRD metric or a technical requirement (provenance, surrogate key, etc.)

The `mart-review` skill checks this traceability at review time.

## Resources

- `skills/source-discovery/SKILL.md` -- Source discovery workflow (run before BRD for WIKI-like input)
- `templates/business-requirements.template.md` -- BRD template with all sections and placeholders
- `templates/sign-off-prd.template.md` -- Sign-off PRD template (generated alongside TDD as a summary, not a Phase A gate)
- `docs/bus-matrix.md` -- Bus matrix patterns for dimension identification
- `docs/agent-orchestration.md` -- Lifecycle phases and gate definitions
