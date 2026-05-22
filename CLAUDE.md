# mart-forge

Open-source Kimball data-warehouse framework. All code, docs, and examples in this repo are public.

## Confidentiality Gate

**Nothing operator-specific may be committed to this repo.**

Before every commit, verify the diff contains none of the following:

- **Absolute paths** — no `/Users/…`, `C:\Users\…`, `~/…`, Google Drive paths, or any machine-local filesystem reference.
- **Operator identifiers** — no company names, internal project names, Slack/Notion/Linear URLs, or references to private repos beyond `mart-forge` itself.
- **Real positions or credentials** — no real trading positions, account numbers, API keys, tokens, passwords, or PII. Example/seed data must use clearly illustrative values (round numbers, placeholder names).
- **Platform-specific references** — no Shopee, FTMO, prop-firm, or any commercial-platform name unless it is a publicly documented data source used in an example mart (e.g. CBOE).

If in doubt, replace with a placeholder and note the substitution in the PR description.

## Project Rules

- Match existing naming conventions (`docs/naming-conventions.md`).
- Follow the dimensional lifecycle (`docs/dimensional-lifecycle.md`) for new models.
- Every example mart must have a BRD (`templates/business-requirements.template.md`). The sign-off PRD (`sign-off-prd.md`) is a generated summary produced alongside the TDD, not a Phase A gate.
- DQC control catalog is mandatory for all marts (`docs/dqc-framework.md`).
- `target/`, `*.duckdb`, `logs/`, `dbt_packages/` are gitignored — never force-add them.

## Hard Constraints

1. **No `SELECT *`** — every ODS model uses an explicit column list (schema-drift detection).
2. **Provenance on every ODS** — `provider`, `pull_ts_utc`, `quote_ts_utc`, `run_id` are non-negotiable.
3. **Unknown member row** — every DIM includes ID = -1 with all attributes = 'Unknown'.
4. **Idempotency** — no `current_timestamp()` or `now()` in model logic.
5. **Phase gates** — no scaffold without an approved BRD (Phase A) **and** an approved TDD (Phase B).
6. **Window suffixes** — DWS models use `_1d`, `_nd`, `_td`, `_mtd`.

## Skills

| Skill | When to use |
|-------|-------------|
| `using-mart-forge` | **Start here.** Detects lifecycle phase and routes to the right skill. |
| `mart-brd` | Generate a Business Requirements Document from client input (Phase A). |
| `mart-tdd` | Generate a Tech Design Document after BRD approval (Phase B). |
| `mart-bootstrap` | Scaffold a new mart from a `mart.yml` config (Phase C — requires approved BRD + TDD). |
| `dqc-audit` | Audit DQC coverage for an existing mart (Phase D). |
| `schema-evolve` | Propagate source column additions through the layer stack. |
| `mart-review` | Adversarial production-readiness review with graded scorecard. |

## Lifecycle

```
[A] BRD → approval → [B] TDD → approval → [C] Scaffold → [D] DQC → [E] Presentation
```

## Data Layers

| Layer | Naming Pattern | Materialization |
|-------|---------------|-----------------|
| ODS | `{prefix}_ods_{source}_{entity}` | incremental |
| DIM | `{prefix}_dim_{entity}` | table |
| DWD | `{prefix}_dwd_{grain}_{entity}_di` | incremental |
| DWS | `{prefix}_dws_{dims}_{metric}_{window}` | table |
| ADS | `{prefix}_ads_{consumer}_{purpose}` | table |

## Methodology Docs

- `docs/naming-conventions.md` — naming standards
- `docs/dqc-framework.md` — DQC control classes and quality gates
- `docs/bus-matrix.md` — enterprise bus matrix
- `docs/dimensional-lifecycle.md` — SCD types, unknown member pattern
- `docs/agent-orchestration.md` — multi-agent builder/reviewer workflow
- `docs/provider-abstraction.md` — warehouse-agnostic design
- `METHODOLOGY.md` — Kimball fundamentals
