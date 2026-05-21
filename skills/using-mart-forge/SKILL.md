---
name: using-mart-forge
description: |
  Bootstrap skill for the mart-forge framework. Detects which lifecycle phase the user's project is in and routes to the appropriate specialized skill. Start here if you're unsure what to do next.

  **Use when:**
  - "help me build a data warehouse"
  - "where do I start with mart-forge?"
  - "what's the next step for my mart?"
  - User opens a mart-forge project and needs orientation
  - Any ambiguous request that could map to multiple skills

  **Not for:**
  - You already know exactly which skill to invoke (call it directly)
---

# Using mart-forge

Detects the current lifecycle phase of the user's project and routes to the correct specialized skill. This is the entry point for new users and the fallback when intent is ambiguous.

## Lifecycle Phases

```
[A] BRD → [B] TDD → sign-off → [C] Scaffold → [D] DQC → [E] Presentation
```

## Phase Detection

Run these checks in order. The first match determines the phase.

### 1. No project directory

**Signal:** No `mart.yml` or `dbt_project.yml` found in the working directory or any subdirectory.

**Action:** Ask the user what data domain they want to model. Guide them through creating a `mart.yml` using `templates/mart.yml.template` as the starting point. This is pre-Phase A — the user needs to define their domain before any phase begins.

**Artifacts to create:**
- `mart.yml` populated with the user's domain, prefix, grain, providers, schedule, and DQC config

### 2. mart.yml exists, no sign-off PRD

**Signal:** `mart.yml` exists but no `sign-off-prd.md` found (or sign-off PRD exists but sign-off lines are not `approved` / `approved-with-conditions`).

**Phase:** A/B — Business Requirements and Technical Design

**Action:** Route to `mart-bootstrap` Phase A workflow:
1. Validate mart.yml has all required keys
2. Create directory structure
3. Generate sign-off PRD from template
4. STOP and tell the user to review and approve the sign-off PRD

Tell the user: "Your mart config is ready but needs a signed-off design document before scaffolding can begin. Review `sign-off-prd.md` and set both sign-off lines to `approved` when ready."

### 3. Sign-off approved, no models generated

**Signal:** `sign-off-prd.md` exists with both sign-off lines = `approved` or `approved-with-conditions`, but `models/` directory is empty or missing.

**Phase:** C — Scaffold

**Action:** Route to `mart-bootstrap` Phase B workflow. This generates the full dbt project:
- ODS, DIM, DWD, DWS, ADS models
- schema.yml with DQC tests
- Seeds, singular tests, dqc_scorecard.json
- GitHub Actions workflow

Tell the user: "Sign-off is confirmed. Scaffolding the mart now."

### 4. Models exist, DQC incomplete

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

### 5. DQC passes, review needed

**Signal:** All 8 DQC control classes covered, `dqc_scorecard.json` shows all `pass`, but no `review_report.json` exists or the last review grade is below A.

**Phase:** D/E — Review gate

**Action:** Route to `mart-review`:
1. Run adversarial production-readiness review
2. Produce graded scorecard
3. If grade < A, report findings and remediation priority

Tell the user: "DQC looks good. Running a production-readiness review to catch any remaining issues."

### 6. Review passes (grade A)

**Signal:** `review_report.json` exists with grade = A.

**Phase:** E — Presentation (optional)

**Action:** The mart is production-ready. Inform the user:
- "Your mart passed review with grade A. It's ready for production."
- Offer optional next steps: dashboard generation, documentation polish, CI/CD setup verification

### 7. Existing mart, schema change

**Signal:** User mentions a new column, source schema change, or field addition.

**Action:** Route to `schema-evolve`. This is a lateral operation that can happen at any phase after Phase C.

## Ambiguous Requests

If the user's request doesn't clearly map to a phase:

| User says | Route to |
|-----------|----------|
| "build a warehouse" / "scaffold" / "create a mart" | Phase detection above |
| "check quality" / "run tests" / "audit" | `dqc-audit` |
| "is it ready?" / "review" / "grade" | `mart-review` |
| "new column" / "schema changed" / "add field" | `schema-evolve` |
| "what's wrong?" / "why is it failing?" | `dqc-audit` first, then `mart-review` if DQC passes |

## Resources

- `CLAUDE.md` — Project constraints and methodology quick-reference
- `METHODOLOGY.md` — Kimball fundamentals
- `templates/mart.yml.template` — Starter mart config
- `docs/` — Full methodology documentation
- `examples/gme-options-mart/` — Working reference implementation
