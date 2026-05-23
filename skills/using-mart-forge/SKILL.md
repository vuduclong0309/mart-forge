---
name: using-mart-forge
description: |
  Bootstrap skill for the mart-forge framework. Detects which lifecycle phase the user's project is in and routes to the appropriate specialized skill. Start here if you're unsure what to do next.

  **Use when:**
  - "help me build a data warehouse"
  - "where do I start with mart-forge?"
  - "what's the next step for my mart?"
  - User opens a mart-forge project and needs orientation
  - User provides a wiki page, stakeholder brief, or domain description
  - Any ambiguous request that could map to multiple skills

  **Not for:**
  - You already know exactly which skill to invoke (call it directly)
---

# Using mart-forge

Detects the current lifecycle phase of the user's project and routes to the correct specialized skill. This is the entry point for new users and the fallback when intent is ambiguous.

## Lifecycle Phases

```
[A0] Source Discovery → [A] BRD → approval → [B] TDD → approval → [C] Scaffold → [D] DQC → [E] Dashboard
```

Phase A0 (Source Discovery) is optional but strongly recommended when the user starts from a narrative
document, wiki page, or stakeholder brief rather than a known data pipeline.

## Phase Detection

Run these checks in order. The first match determines the phase.

### 0. User provides a WIKI-like document or domain description (no project yet)

**Signal:** The user pastes or references a wiki page, stakeholder brief, product spec, or domain
description — and no `mart.yml` or `dbt_project.yml` is present.

**Phase:** A0 — Source Discovery

**Action:** Route to `source-discovery` before anything else:
1. Parse the document for domain, metrics, and candidate data sources
2. Enumerate sources with availability, auth, license, freshness, and schema
3. Classify metrics as PUBLIC / PRIVATE / UNVERIFIED / UNSUPPORTED
4. Produce a source catalog for BRD Section 4
5. STOP and present findings — ask the user whether to proceed to BRD or resolve open items

Tell the user: "I can see you've provided a stakeholder document. Let me first discover and vet the
available data sources before we write requirements. Run `/source-discovery` to enumerate what data
you can actually get, then proceed to `/mart-brd`."

### 1. No project directory

**Signal:** No `mart.yml` or `dbt_project.yml` found in the working directory or any subdirectory,
and the user has NOT provided a WIKI-like input document.

**Action:** Ask the user what data domain they want to model. Guide them through creating a `mart.yml`
using `templates/mart.yml.template` as the starting point. This is pre-Phase A — the user needs to
define their domain before any phase begins.

**Artifacts to create:**
- `mart.yml` populated with the user's domain, prefix, grain, providers, schedule, and DQC config

### 2. mart.yml exists, no BRD (or BRD not approved)

**Signal:** `mart.yml` exists but no `business-requirements.md` found (or BRD exists but sign-off
lines are not `approved` / `approved-with-conditions`).

**Phase:** A — Business Requirements

**Action:** Route to `mart-brd`:
1. Gather client input (case study, data files, verbal description, or source catalog from A0)
2. Produce `business-requirements.md` from template
3. STOP and tell the user to review and approve the BRD

Tell the user: "Your mart config is ready but needs a Business Requirements Document before technical
design can begin. Run `/mart-brd` to generate it, then set both sign-off lines to `approved` when ready."

**Note:** If a source catalog was produced by `/source-discovery`, pass it to `/mart-brd` so that
Section 4 sources are tagged [CONFIRMED] rather than [ASSUMED].

### 3. BRD approved, no TDD (or TDD not approved)

**Signal:** `business-requirements.md` exists with both sign-off lines = `approved` or
`approved-with-conditions`, but no `tech-design-doc.md` found (or TDD exists but sign-off lines
are not approved).

**Phase:** B — Technical Design

**Action:** Route to `mart-tdd`:
1. Read approved BRD and mart.yml
2. Produce `tech-design-doc.md` with column-level specs (+ `sign-off-prd.md` as a generated summary)
3. STOP and tell the user to review and approve the TDD

Tell the user: "BRD is approved. Generate the Tech Design Document with `/mart-tdd`, then set both
sign-off lines to `approved` when ready."

### 4. BRD and TDD approved, no models generated

**Signal:** Both `business-requirements.md` and `tech-design-doc.md` have approved sign-off lines,
but `models/` directory is empty or missing.

**Phase:** C — Scaffold

**Action:** Route to `mart-bootstrap` scaffold workflow. This generates the full dbt project:
- ODS, DIM, DWD, DWS, ADS models
- schema.yml with DQC tests
- Seeds, singular tests, dqc_scorecard.json
- GitHub Actions workflow
- Runs `dbt compile` to verify the scaffold is syntactically valid before reporting success

Tell the user: "Both design documents are signed off. Scaffolding the mart now."

### 5. Models exist, DQC incomplete

**Signal:** Model `.sql` files exist under `models/`, but one or more of:
- `dqc_scorecard.json` missing or has `fail`/`pending` entries
- `dbt test` has not been run or has failures
- Coverage gaps in the 8 DQC control classes

**Phase:** D — DQC Verification

**Action:** Route to `dqc-audit`:
1. Run the full DQC audit workflow
2. Produce coverage matrix and gap analysis
3. If gaps found, suggest fixes or route to `schema-evolve` for missing test coverage

Tell the user: "Your mart has models but DQC verification is incomplete. Running an audit to identify gaps."

### 6. DQC passes, review needed

**Signal:** All 8 DQC control classes covered, `dqc_scorecard.json` shows all `pass`, but no
`review_report.json` exists or the last review grade is below A.

**Phase:** D/E — Review gate

**Action:** Route to `mart-review`:
1. Run adversarial production-readiness review
2. Produce graded scorecard
3. If grade < A, report findings and remediation priority

Tell the user: "DQC looks good. Running a production-readiness review to catch any remaining issues."

### 7. Review passes (grade A)

**Signal:** `review_report.json` exists with grade = A.

**Phase:** E — Dashboard / Presentation (optional)

**Action:** The mart is production-ready. Inform the user:
- "Your mart passed review with grade A. It's ready for production."
- Offer optional next steps: dashboard generation, documentation polish, CI/CD setup verification

### 8. Existing mart, schema change

**Signal:** User mentions a new column, source schema change, or field addition.

**Action:** Route to `schema-evolve`. This is a lateral operation that can happen at any phase
after Phase C.

## Ambiguous Requests

If the user's request doesn't clearly map to a phase:

| User says | Route to |
|-----------|----------|
| "here's our wiki" / "here's the spec" / WIKI-like input | `source-discovery` (Phase A0) |
| "what data can I get?" / "verify these sources" | `source-discovery` |
| "build a warehouse" / "scaffold" / "create a mart" | Phase detection above |
| "check quality" / "run tests" / "audit" | `dqc-audit` |
| "is it ready?" / "review" / "grade" | `mart-review` |
| "new column" / "schema changed" / "add field" | `schema-evolve` |
| "what's wrong?" / "why is it failing?" | `dqc-audit` first, then `mart-review` if DQC passes |

## WIKI-to-Mart Guided Path

When a user starts from a WIKI-like document, the guided path is:

```
1. /source-discovery   — paste the WIKI; get back a vetted source catalog
2. /mart-brd           — source catalog feeds Section 4; BRD captures requirements
3. operator approves BRD sign-off
4. /mart-tdd           — approved BRD drives column-level design
5. operator approves TDD sign-off
6. /mart-bootstrap     — scaffolds dbt project; runs dbt compile to verify
7. /dqc-audit          — verify all 8 DQC control classes pass
8. /mart-review        — adversarial readiness review; target grade A
9. (optional) dashboard generation or CI/CD setup
```

Each step produces a STOP + human gate before the next phase starts.

## Resources

- `CLAUDE.md` — Project constraints and methodology quick-reference
- `METHODOLOGY.md` — Kimball fundamentals
- `templates/mart.yml.template` — Starter mart config
- `docs/` — Full methodology documentation
- `skills/source-discovery/SKILL.md` — Source discovery workflow
- `examples/gme-options-mart/` — Working reference implementation
