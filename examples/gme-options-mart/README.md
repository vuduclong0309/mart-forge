# GME Options Mart

> **Educational Use Only / Not Financial Advice.** This example mart uses freely available delayed market data from CBOE for educational and framework demonstration purposes. It does not constitute financial advice, trading signals, or investment recommendations. The warrant monitoring columns use illustrative example values, not real positions. Use at your own risk.

Canonical example mart for the mart-forge framework. Demonstrates a complete Kimball data warehouse built on **live CBOE delayed options data** using dbt + DuckDB with httpfs.

## Quick Start

```bash
cd examples/gme-options-mart
pip install dbt-core dbt-duckdb
dbt seed --profiles-dir .
dbt run --profiles-dir .
dbt test --profiles-dir .
```

## Architecture

**Grain:** per-contract-per-day

### Data Layers

| Layer | Models | Description |
|-------|--------|-------------|
| ODS | `gme_ods_cboe_options_chain` | Live ingestion from CBOE delayed quotes via httpfs (read_json_auto) |
| DIM | `gme_dim_date` | Conformed date dimension with trading day flag (seeded 2024-2027) |
| DWD | `gme_dwd_option_contract_di` | Cleaned option contracts with GEX computed, series classified |
| DWS | `gme_dws_strike_gex_1d`, `gme_dws_daily_snapshot_1d` | Strike-level GEX + daily summary (max pain, P/C ratio, top OI) |
| ADS | `gme_ads_warrant_dashboard` | One-big-table combining market snapshot with illustrative warrant monitor |

### Data Source

CBOE provides free delayed options quotes (15-min lag) at `cdn.cboe.com`. The ODS model uses DuckDB's httpfs extension to read JSON directly — no API key, no Python scripts, no intermediate files.

Each pull returns ~1300 option contracts with full Greeks (delta, gamma, theta, vega, rho, IV) computed by CBOE.

## Bus Matrix

```
                              dim_date
gme_dwd_option_contract_di       X
gme_dws_strike_gex_1d            X
gme_dws_daily_snapshot_1d        X
gme_ads_warrant_dashboard        X
```

## Key Derived Metrics

| Metric | Formula | Layer |
|--------|---------|-------|
| GEX contribution | `gamma * OI * 100 * spot^2 * 0.01 * sign(call=+1, put=-1)` | DWD |
| Max pain | Strike minimizing total exercise value across all contracts | DWS |
| P/C ratio | Put OI / Call OI | DWS |
| Warrant moneyness | `(spot - strike) / strike * 100` | ADS |

## DQC Control Catalog

All 8 control classes implemented:

| Control Class | Implementation | Status |
|---------------|----------------|--------|
| PK Integrity | `not_null` + `unique` on all PKs | pass |
| FK Integrity | ADS pull_date resolves to dim_date | pass |
| Freshness | Singular test on `pull_ts_utc` | pass |
| Completeness / Volume | Singular test on minimum row counts | pass |
| Accepted Ranges | Positive strikes, non-negative OI, plausible P/C ratio | pass |
| Duplicate Detection | Singular test on `(pull_date, option_symbol)` grain | pass |
| Null-Rate Threshold | Greeks null rate < 5% in DWD | pass |
| Business Reconciliation | GEX vs external source — **unavailable** (paywalled, waiver granted) | unavailable |

See `dqc_scorecard.json` for the machine-readable scorecard.

## Customization

The `dbt_project.yml` includes configurable variables for the warrant monitoring ADS layer:

```yaml
vars:
  warrant_strike: 30.0       # example strike price
  warrant_quantity: 100       # example contract count
  warrant_expiry: '2026-12-18'  # example expiry date
```

Replace these with your own values or remove the `gme_ads_warrant_dashboard` model if warrant monitoring is not relevant to your use case.
