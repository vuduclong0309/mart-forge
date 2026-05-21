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
- Every example mart must have a sign-off PRD (`templates/sign-off-prd.template.md`).
- DQC control catalog is mandatory for all marts (`docs/dqc-framework.md`).
- `target/`, `*.duckdb`, `logs/`, `dbt_packages/` are gitignored — never force-add them.
