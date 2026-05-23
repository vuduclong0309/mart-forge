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
| IV30 | [MarketChameleon](https://marketchameleon.com/Overview/GME/IV/) |
| Gamma Flip | [SqueezeMetrics](https://squeezemetrics.com/monitor/dix) |
| HV20 | [MarketChameleon](https://marketchameleon.com/Overview/GME/IV/) |
| IV Rank / Percentile | [MarketChameleon](https://marketchameleon.com/Overview/GME/IV/) |
| Dealer Net Gamma | [SqueezeMetrics](https://squeezemetrics.com/monitor/dix) |
| OI Daily Delta | [Barchart](https://www.barchart.com/stocks/quotes/GME/options-overview) |

## Architecture

**Grain:** per-contract-per-day

### Data Layers

| Layer | Models | Description |
|-------|--------|-------------|
| ODS | `gme_ods_cboe_options_chain` | Fixture-backed by default (Parquet); live CBOE via httpfs when `use_fixture: false` |
| DIM | `gme_dim_date` | Conformed date dimension with trading day flag (seeded 2024-2027) |
| DWD | `gme_dwd_option_contract_di` | Cleaned option contracts with GEX computed, series classified |
| DWS | `gme_dws_strike_gex_1d`, `gme_dws_daily_snapshot_1d`, `gme_dws_options_metrics_1d` | Strike-level GEX + daily summary + Phase-1 options metrics |
| ADS | `gme_ads_market_dashboard` | One-big-table combining market snapshot, Phase-1 metrics, and calendar attributes |

### Data Source

By default, the ODS reads from `fixtures/gme_ods_cboe_options_chain.parquet` — an illustrative snapshot of 20 option contracts with full Greeks (delta, gamma, theta, vega, rho, IV). This makes the example fully offline and deterministic. See `fixtures/MANIFEST.md` for provenance, schema hash, and captured values.

> **Fixture values are illustrative CI data.** The spot price (28.50) and all derived metrics in fixture mode do not represent current or historical market conditions. Set `use_fixture: false` for live delayed data from CBOE.

To switch to live data, set `use_fixture: false` in `dbt_project.yml`. CBOE provides free delayed quotes (15-min lag) at `cdn.cboe.com`; the ODS model uses DuckDB's httpfs extension to read JSON directly — no API key or intermediate files needed.

### Underlying Closes Seed

`seeds/gme_underlying_closes.csv` contains 260 trading days of GME daily closing prices (2025-05-08 to 2026-05-20) sourced from the Yahoo Finance chart API (`query2.finance.yahoo.com/v8/finance/chart/GME`). This seed powers the HV20 (20-day historical volatility) metric in `gme_dws_options_metrics_1d`.

To refresh: re-fetch from `https://query2.finance.yahoo.com/v8/finance/chart/GME?period1=<start_epoch>&period2=<end_epoch>&interval=1d&events=history`, extract timestamps and closes, and overwrite the CSV. The seed is deterministic for CI once committed; live refresh is optional.

## Bus Matrix

```
                              dim_date  gme_underlying_closes
gme_dwd_option_contract_di       X
gme_dws_strike_gex_1d            X
gme_dws_daily_snapshot_1d        X
gme_dws_options_metrics_1d       X            X
gme_ads_market_dashboard         X
```

## Key Derived Metrics

| Metric | Formula | Layer |
|--------|---------|-------|
| GEX contribution | `gamma * OI * 100 * spot^2 * 0.01 * sign(call=+1, put=-1)` | DWD |
| Max pain | Strike minimizing total exercise value across all contracts | DWS |
| P/C ratio | Put OI / Call OI | DWS |
| Gamma flip point | Strike where cumulative net GEX crosses zero (interpolated); fallback: nearest-to-zero strike | DWS |
| IV30 | OI-weighted average IV for near-30-DTE contracts (20-40 DTE window) | DWS |
| HV20 | `STDDEV(ln(close/prev_close)) * SQRT(252)` over 20 trading days; uses `gme_underlying_closes` seed | DWS |
| IV Rank | `(iv30 - min_iv30_252d) / (max_iv30_252d - min_iv30_252d)`; NULL when < 20 days history | DWS |
| OI daily delta | `total_oi(today) - total_oi(yesterday)` via LAG; NULL on first observation | DWS |
| Dealer net gamma | Sum of per-contract GEX contribution (dollar gamma exposure) | DWS |
| IV Percentile | Fraction of 252-day window where IV30 < current IV30; NULL when < 20 days history | DWS |

## OpenBB Provider Probe

OpenBB Platform is registered as a reconciliation provider for independent GEX cross-verification. A probe script tests each OpenBB provider for GME options chain data:

```bash
uv venv /tmp/openbb-probe && source /tmp/openbb-probe/bin/activate
uv pip install 'openbb>=4.5' openbb-tradier
python scripts/openbb_gex_probe.py --pretty
```

The probe classifies each provider automatically. Statuses in this table and in `dqc_scorecard.json` are reproducible by re-running the script:

| Provider | Probe Status | Reason |
|----------|-------------|--------|
| `cboe` | `not_independent` | Same cdn.cboe.com endpoint as primary ODS — independence guard, skipped before API call |
| `yfinance` | `insufficient_fields` | Returns contracts but **no gamma column** — GEX not computable |
| `intrinio` | `credentials_required` | Paid API key (`intrinio_api_key`) needed |
| `tradier` | `credentials_required` | Available via `openbb-tradier`; requires `tradier_api_key` |

Unsupported providers (if probed in the future) are classified as `not_available`.

Re-run the probe when providers update to check if business reconciliation can upgrade from proxy to direct.

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
