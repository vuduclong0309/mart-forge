# Fixture Manifest

This directory contains static data fixtures used for offline CI and framework
demonstration. **All values are illustrative historical CI data** — they do not
represent current market conditions and must not be interpreted as live analytics.

## gme_ods_cboe_options_chain.parquet

| Field | Value |
|-------|-------|
| **Purpose** | Deterministic offline CI and framework demonstration |
| **Source format** | CBOE delayed-quotes JSON schema (manually constructed) |
| **Provider URL** | `https://cdn.cboe.com/api/global/delayed_quotes/options/GME.json` |
| **Fixture pull_date** | 2026-05-20 |
| **Captured spot (underlying_close)** | 28.50 (illustrative; not a real-time market value) |
| **Row count** | 20 option contracts |
| **Schema columns** | 34 (matches live CBOE ingestion schema) |
| **File SHA-256** | `2bccc54cd65788a8e55906fae62dcf2ab5cb5cdf46c6510e75cb6669a6741d95` |
| **Created** | 2026-05-20 |

### Important

- The `underlying_close` value of **28.50** is a round illustrative number chosen
  for the fixture. It does not correspond to an actual GME closing price on any
  specific date. Do not cite it as a current or historical market price.
- The `run_id` is set to `manual`, indicating this fixture was hand-crafted for
  CI reproducibility, not captured from a live CBOE API pull.
- When the dashboard or pipeline runs with `use_fixture: true` (the default),
  all derived metrics (GEX, max pain, P/C ratio, IV30, etc.) are computed from
  this static snapshot and are not reflective of current market conditions.
