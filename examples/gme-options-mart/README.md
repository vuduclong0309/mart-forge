# GME Options Mart

> **Educational Use Only / Not Financial Advice.** This example mart uses freely available delayed market data from CBOE for educational and framework demonstration purposes. It does not constitute financial advice, trading signals, or investment recommendations. Use at your own risk.

Canonical example mart for the mart-forge framework. Demonstrates a complete Kimball data warehouse using dbt + DuckDB. Runs **offline by default** using a bundled Parquet fixture; set `use_fixture: false` in `dbt_project.yml` to pull live delayed data from CBOE via httpfs.

## Quick Start

```bash
cd examples/gme-options-mart
pip install dbt-core dbt-duckdb
dbt seed --profiles-dir .
dbt run --profiles-dir .
dbt test --profiles-dir .
```

### Dashboard

```bash
pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py
```

Every metric card links to a free public reference site for independent verification:

| Metric | Fact-Check Source |
|--------|-------------------|
| Spot Price | [Yahoo Finance](https://finance.yahoo.com/quote/GME) |
| Max Pain | [SwaggyStocks](https://swaggystocks.com/dashboard/options-max-pain/GME) |
| P/C Ratio | [Barchart](https://www.barchart.com/stocks/quotes/GME/options-overview) |
| Net GEX | [SqueezeMetrics](https://squeezemetrics.com/monitor/dix) |
| IV / Convergence | [MarketChameleon](https://marketchameleon.com/Overview/GME/IV/) |

## Architecture

**Grain:** per-contract-per-day

### Data Layers

| Layer | Models | Description |
|-------|--------|-------------|
| ODS | `gme_ods_cboe_options_chain` | Fixture-backed by default (Parquet); live CBOE via httpfs when `use_fixture: false` |
| DIM | `gme_dim_date` | Conformed date dimension with trading day flag (seeded 2024-2027) |
| DWD | `gme_dwd_option_contract_di` | Cleaned option contracts with GEX computed, series classified |
| DWS | `gme_dws_strike_gex_1d`, `gme_dws_daily_snapshot_1d` | Strike-level GEX + daily summary (max pain, P/C ratio, top OI) |
| ADS | `gme_ads_market_dashboard` | One-big-table combining market snapshot with calendar attributes |

### Data Source

By default, the ODS reads from `fixtures/gme_ods_cboe_options_chain.parquet` — a bundled snapshot of ~1300 option contracts with full Greeks (delta, gamma, theta, vega, rho, IV). This makes the example fully offline and deterministic.

To switch to live data, set `use_fixture: false` in `dbt_project.yml`. CBOE provides free delayed quotes (15-min lag) at `cdn.cboe.com`; the ODS model uses DuckDB's httpfs extension to read JSON directly — no API key or intermediate files needed.

## Bus Matrix

```
                              dim_date
gme_dwd_option_contract_di       X
gme_dws_strike_gex_1d            X
gme_dws_daily_snapshot_1d        X
gme_ads_market_dashboard         X
```

## Key Derived Metrics

| Metric | Formula | Layer |
|--------|---------|-------|
| GEX contribution | `gamma * OI * 100 * spot^2 * 0.01 * sign(call=+1, put=-1)` | DWD |
| Max pain | Strike minimizing total exercise value across all contracts | DWS |
| P/C ratio | Put OI / Call OI | DWS |

## OpenBB Provider Probe

OpenBB Platform is registered as a reconciliation provider for independent GEX cross-verification. A probe script tests each OpenBB provider for GME options chain data:

```bash
uv venv /tmp/openbb-probe && source /tmp/openbb-probe/bin/activate
uv pip install 'openbb>=4.5' openbb-tradier
python scripts/openbb_gex_probe.py --pretty
```

Providers attempted (OpenBB 4.7.1, openbb-tradier 1.5.0, 2026-05-22):

| Provider | Result | Reason |
|----------|--------|--------|
| `cboe` | not independent | Same cdn.cboe.com endpoint as primary ODS — not a separate source |
| `yfinance` | insufficient fields | Returns 905 contracts but **no gamma column** — GEX not computable |
| `intrinio` | credentials required | Paid API key (`intrinio_api_key`) needed |
| `tradier` | credentials required | Available via `openbb-tradier`; requires `tradier_api_key` |

If a future OpenBB provider or yfinance update adds gamma to the response, re-run the probe to upgrade business reconciliation from proxy to direct.

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
| Business Reconciliation | GEX vs external — OpenBB probed, no free gamma source; proxy in place | exhausted |

See `dqc_scorecard.json` for the machine-readable scorecard with full `attempts[]` evidence. The dashboard displays a DQC status badge derived from this file.
