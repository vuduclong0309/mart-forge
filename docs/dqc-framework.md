# Data Quality Contract (DQC) Framework

<!-- Three-tier data quality contract specification. -->

## Tier 1: Generic Tests
dbt schema tests (unique, not_null, accepted_values, relationships) applied via `schema.yml`.

## Tier 2: Singular Business-Logic Tests
Custom SQL tests under `tests/` that encode domain-specific invariants (e.g., revenue reconciliation, grain enforcement).

## Tier 3: External Reconciliation
Cross-reference mart outputs against authoritative external sources. Results captured in `dqc_scorecard.json`.
