# Tech Design Document: GME Options Mart

> Version 1.0 — Open-source example for the mart-forge framework.

---

## Changelog

| Version | Description | Date | Editor |
|---------|-------------|------|--------|
| V1.0 | Initial TDD authored from final built mart (post DATA-01/02/03) | 2026-05-23 | mart-forge maintainers |

---

## 1. Business Background Understanding

The GME Options Mart is a Kimball data warehouse that captures, transforms, and aggregates daily options chain data for GameStop Corp (GME). The mart answers questions about gamma exposure positioning, max pain convergence, put/call sentiment, implied vs. historical volatility, and social sentiment — all from publicly available data.

The primary data source is CBOE delayed quotes (~1,300 option contracts per pull, 15-minute delay). Supplementary sources include Yahoo Finance daily underlying closes (for HV20 computation) and social sentiment aggregates (Reddit/social fixture). The mart operates on a daily grain with an 8:45 PM ET weekday cron schedule.

Refer to `business-requirements.md` for the full BRD including metrics catalog, domain glossary, data sources, and stakeholder personas.

---

## 2. Metrics Breakdown

Metrics are organized by analytical category. Each metric traces to a specific SQL model with an exact computation formula.

### Exposure Metrics
- **GEX contribution** (per-contract): `gamma * OI * 100 * spot² * 0.01 * sign(call=+1, put=-1)`
- **Net GEX** (strike-level): `SUM(gex_contribution)` grouped by strike
- **Net GEX** (daily total): `SUM(net_gex)` across all strikes
- **Dealer net gamma**: `SUM(gex_contribution)` across all contracts for the day
- **Gamma flip point**: Linear interpolation of the strike where cumulative net GEX crosses zero

### Pain & Positioning Metrics
- **Max pain strike**: Cross-join strike candidates; select strike with `MIN(SUM(ITM exercise pain))`
- **Max pain convergence %**: `ABS(spot - max_pain_strike) / spot * 100`
- **P/C ratio**: `SUM(put_OI) / SUM(call_OI)`
- **Top OI strikes (1/2/3)**: Strikes ranked by `SUM(open_interest) DESC`

### Volatility Metrics
- **IV30**: OI-weighted IV for contracts with DTE ∈ [20, 40]: `SUM(IV * OI) / SUM(OI)`
- **HV20**: `STDDEV(LN(close/prev_close)) * SQRT(252)` over 20 log-returns from underlying closes
- **IV rank**: `(current_iv30 - min_iv30_252d) / (max_iv30_252d - min_iv30_252d)` — NULL if < 20 sessions
- **IV percentile**: `days_below / iv30_day_count` over 252-session window — NULL if < 20 sessions

### Flow Metrics
- **OI daily delta**: `total_oi(today) - LAG(total_oi) OVER (ORDER BY pull_date)` — NULL on first observation

### Sentiment Metrics
- **Social mention count**: `SUM(mention_count)` per day
- **Social sentiment score**: `SUM(sentiment_score * mention_count) / SUM(mention_count)` (mention-weighted)

---

## 3. Design Consideration

Following the Kimball 4-step dimensional design process:

### 3.1 Get the Business Process

The business process is **daily options market microstructure analysis**: capturing an end-of-day snapshot of the full GME options chain and deriving exposure, pain, volatility, and sentiment metrics for dashboard consumption.

### 3.2 Declare the Grain

**Fact grain:** One row per option contract per pull date.

This is the most atomic grain available from the CBOE source. Each row represents a single option contract (identified by its OCC symbol) on a specific trading day. All summary metrics are aggregated upward from this grain.

### 3.3 Identify the Dimensions

The dimension space for options market data is narrow. Option contracts are identified by degenerate dimensions (ticker, strike, expiry, option_type, option_symbol) carried directly in the fact table rather than as separate dimension tables.

The single conformed dimension is:
- **gme_dim_date** — a calendar dimension with trading day flags, seeded from CSV (2024–2027)

Degenerate dimensions in the fact table:
- `ticker` — always 'GME' in this mart (single-ticker design)
- `strike` — option strike price
- `expiry` — option expiration date
- `option_type` — 'call' or 'put'
- `option_symbol` — OCC-format unique contract identifier
- `series_type` — WEEKLY / MONTHLY / LEAP (derived from DTE)

### 3.4 Identify the Facts

Facts fall into two categories:

**Additive facts** (can be summed across dimensions):
- `open_interest` — total outstanding contracts
- `volume` — contracts traded
- `gex_contribution` — dollar-denominated gamma exposure

**Non-additive / semi-additive facts** (cannot be freely summed):
- `implied_vol`, `delta`, `gamma`, `theta`, `vega`, `rho` — per-contract Greeks (must be averaged or OI-weighted)
- `bid`, `ask`, `mid_price`, `last_trade_price` — prices (must use latest, not sum)
- `spot` — underlying close (same for all contracts on a given day)

**Derived metrics** (computed in DWS/ADS layers):
- `net_gex`, `max_pain_strike`, `pc_ratio`, `gamma_flip_point`, `iv30`, `hv20`, `iv_rank`, `iv_percentile`, `oi_daily_delta`, `dealer_net_gamma`, `social_mention_count`, `social_sentiment_score`

---

## 4. Bus Matrix

| Business Process | ODS | DIM | DWD | DWS | ADS | Dimensions Used |
|------------------|-----|-----|-----|-----|-----|-----------------|
| Options chain ingestion | gme_ods_cboe_options_chain | not applicable | not applicable | not applicable | not applicable | pull_date, option_symbol |
| Contract-level fact | not applicable | not applicable | gme_dwd_option_contract_di | not applicable | not applicable | pull_date, option_symbol, strike, expiry, option_type, ticker |
| Calendar | not applicable | gme_dim_date | not applicable | not applicable | not applicable | date_key, full_date |
| Strike-level GEX aggregation | not applicable | not applicable | not applicable | gme_dws_strike_gex_1d | not applicable | pull_date, ticker, strike, expiry |
| Daily market snapshot | not applicable | not applicable | not applicable | gme_dws_daily_snapshot_1d | not applicable | pull_date, ticker |
| Phase-1 options metrics | not applicable | not applicable | not applicable | gme_dws_options_metrics_1d | not applicable | pull_date, ticker |
| Social sentiment daily | not applicable | not applicable | not applicable | gme_dws_social_sentiment_1d | not applicable | pull_date, ticker |
| Dashboard OBT | not applicable | not applicable | not applicable | not applicable | gme_ads_market_dashboard | pull_date, ticker + dim_date attrs |

---

## 5. Table Summary

### Naming Convention

| Layer | Pattern | Example |
|-------|---------|---------|
| ODS | `{prefix}_ods_{source}_{entity}` | gme_ods_cboe_options_chain |
| DIM | `{prefix}_dim_{dimension_name}` | gme_dim_date |
| DWD | `{prefix}_dwd_{entity}_{grain_suffix}` | gme_dwd_option_contract_di |
| DWS | `{prefix}_dws_{metric_group}_{window}` | gme_dws_strike_gex_1d |
| ADS | `{prefix}_ads_{purpose}` | gme_ads_market_dashboard |

### Data Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           ADS (Consumption)                             │
│                                                                         │
│                     gme_ads_market_dashboard                            │
│                     (one-big-table for dashboard)                       │
│                              ▲                                          │
├──────────────────────────────┼──────────────────────────────────────────┤
│                           DWS (Summary)                                 │
│                              │                                          │
│  ┌────────────────┐  ┌───────┴────────┐  ┌──────────────────────────┐  │
│  │ strike_gex_1d  │  │ snapshot_1d    │  │ options_metrics_1d       │  │
│  │ (per-strike)   │  │ (per-day)      │  │ (per-day)                │  │
│  └───────┬────────┘  └───────┬────────┘  └─────────┬────────────────┘  │
│          │                   │                     │                    │
│          │           ┌───────┴────────┐    ┌───────┴──────────────┐    │
│          │           │                │    │ social_sentiment_1d  │    │
│          │           │                │    │ (per-day)            │    │
│          │           │                │    └──────────────────────┘    │
├──────────┼───────────┼────────────────┼────────────────────────────────┤
│                         DWD (Detail Fact)                               │
│                              │                                          │
│              gme_dwd_option_contract_di                                 │
│              (per-contract-per-day, filtered)                           │
│                              ▲                                          │
├──────────────────────────────┼──────────────────────────────────────────┤
│            ODS (Raw Ingestion)      │      DIM (Dimensions)            │
│                              │      │                                   │
│   gme_ods_cboe_options_chain │      │      gme_dim_date ◄── dim_date   │
│   (per-contract-per-pull)    │      │                        (seed)    │
│              ▲               │      │                                   │
│              │               │      │      Seeds:                       │
│     ┌────────┴────────┐      │      │      - gme_underlying_closes     │
│     │ CBOE JSON API   │      │      │      - gme_social_sentiment      │
│     │ (or Parquet     │      │      │                                   │
│     │  fixture)       │      │      │                                   │
│     └─────────────────┘      │      │                                   │
└──────────────────────────────┴──────┴───────────────────────────────────┘
```

---

## 6. Table Schema Detail

### 6.1 ODS Layer

#### gme_ods_cboe_options_chain

- **Source:** CBOE delayed quotes JSON API (httpfs) or bundled Parquet fixture
- **Materialization:** Incremental
- **Incremental strategy:** `delete+insert` (dbt-duckdb; `merge` is not supported by this adapter)
- **Logical partition column:** `pull_date` (daily grain — one snapshot per trading day)
- **Unique key:** `['pull_date', 'option_symbol']`
- **Grain:** One row per option contract per pull date
- **Refresh frequency:** Daily (8:45 PM ET, weekdays)
- **Pre-hook:** `http_retry_config(timeout_ms=30000, retries=3)`
- **Backfill protocol:** Set `--var backfill:true` to bypass the incremental date filter and reprocess all historical dates. Without this flag, only rows with `pull_date >= MAX(pull_date)` from the prior build are processed.
- **Restatement handling:** The `delete+insert` strategy on `(pull_date, option_symbol)` ensures that rerunning the same pull date replaces existing rows rather than appending duplicates. Same-day reruns are fully idempotent.

| column_name | data_type | definition | example_value | calculation | data_source |
|-------------|-----------|-----------|---------------|-------------|-------------|
| pull_date | DATE | Date the options chain was pulled | 2026-05-20 | `CURRENT_DATE` (live) or from fixture | CBOE / fixture |
| ticker | VARCHAR | Underlying ticker symbol | GME | Hardcoded `'GME'` (live) or from fixture | CBOE / fixture |
| provider | VARCHAR | Data provider identifier | cboe | Hardcoded `'cboe'` (live) or from fixture | CBOE / fixture |
| pull_ts_utc | TIMESTAMP | Timestamp when the data was captured | 2026-05-20 20:45:00 | `CAST(cboe_timestamp AS TIMESTAMP)` | CBOE timestamp field |
| quote_ts_utc | TIMESTAMP | Timestamp of the quote snapshot | 2026-05-20 20:45:00 | `CAST(cboe_timestamp AS TIMESTAMP)` | CBOE timestamp field |
| run_id | VARCHAR | Pipeline run identifier | manual | `var("run_id", "manual")` | Pipeline variable |
| option_symbol | VARCHAR | OCC-format option contract identifier | GME260620C00025000 | `elem['option']` from JSON array | CBOE options[].option |
| bid | DOUBLE | Best bid price | 3.50 | `CAST(elem['bid'] AS DOUBLE)` | CBOE options[].bid |
| bid_size | INTEGER | Number of contracts at best bid | 10 | `CAST(elem['bid_size'] AS INT)` | CBOE options[].bid_size |
| ask | DOUBLE | Best ask price | 3.80 | `CAST(elem['ask'] AS DOUBLE)` | CBOE options[].ask |
| ask_size | INTEGER | Number of contracts at best ask | 15 | `CAST(elem['ask_size'] AS INT)` | CBOE options[].ask_size |
| iv | DOUBLE | CBOE-computed implied volatility | 0.85 | `CAST(elem['iv'] AS DOUBLE)` | CBOE options[].iv |
| open_interest | INTEGER | Outstanding contracts | 5000 | `CAST(elem['open_interest'] AS INT)` | CBOE options[].open_interest |
| volume | INTEGER | Contracts traded today | 200 | `CAST(elem['volume'] AS INT)` | CBOE options[].volume |
| delta | DOUBLE | Option delta | 0.45 | `CAST(elem['delta'] AS DOUBLE)` | CBOE options[].delta |
| gamma | DOUBLE | Option gamma | 0.03 | `CAST(elem['gamma'] AS DOUBLE)` | CBOE options[].gamma |
| theta | DOUBLE | Option theta (time decay) | -0.05 | `CAST(elem['theta'] AS DOUBLE)` | CBOE options[].theta |
| vega | DOUBLE | Option vega (vol sensitivity) | 0.12 | `CAST(elem['vega'] AS DOUBLE)` | CBOE options[].vega |
| rho | DOUBLE | Option rho (rate sensitivity) | 0.02 | `CAST(elem['rho'] AS DOUBLE)` | CBOE options[].rho |
| theo | DOUBLE | Theoretical option value | 3.65 | `CAST(elem['theo'] AS DOUBLE)` | CBOE options[].theo |
| change | DOUBLE | Price change from previous close | 0.25 | `CAST(elem['change'] AS DOUBLE)` | CBOE options[].change |
| opt_open | DOUBLE | Option open price | 3.40 | `CAST(elem['open'] AS DOUBLE)` | CBOE options[].open |
| opt_high | DOUBLE | Option high price | 3.90 | `CAST(elem['high'] AS DOUBLE)` | CBOE options[].high |
| opt_low | DOUBLE | Option low price | 3.30 | `CAST(elem['low'] AS DOUBLE)` | CBOE options[].low |
| tick | VARCHAR | Tick direction indicator | u | `elem['tick']` | CBOE options[].tick |
| last_trade_price | DOUBLE | Price of the last trade | 3.60 | `CAST(elem['last_trade_price'] AS DOUBLE)` | CBOE options[].last_trade_price |
| last_trade_time | VARCHAR | Time of the last trade | 15:45:00 | `elem['last_trade_time']` | CBOE options[].last_trade_time |
| percent_change | DOUBLE | Percentage price change | 7.46 | `CAST(elem['percent_change'] AS DOUBLE)` | CBOE options[].percent_change |
| prev_day_close | DOUBLE | Previous day closing price | 3.35 | `CAST(elem['prev_day_close'] AS DOUBLE)` | CBOE options[].prev_day_close |
| expiry | DATE | Option expiration date (parsed from OCC symbol) | 2026-06-20 | `TRY_CAST('20' \|\| SUBSTRING(CAST(elem['option'] AS VARCHAR), 4, 2) \|\| '-' \|\| SUBSTRING(CAST(elem['option'] AS VARCHAR), 6, 2) \|\| '-' \|\| SUBSTRING(CAST(elem['option'] AS VARCHAR), 8, 2) AS DATE)` | Derived from option_symbol |
| option_type | VARCHAR | Call or put (parsed from OCC symbol) | call | `CASE WHEN SUBSTRING(CAST(elem['option'] AS VARCHAR), 10, 1) = 'C' THEN 'call' ELSE 'put' END` | Derived from option_symbol |
| strike | DOUBLE | Strike price (parsed from OCC symbol, 8-digit / 1000) | 25.0 | `TRY_CAST(SUBSTRING(CAST(elem['option'] AS VARCHAR), 11) AS DOUBLE) / 1000.0` | Derived from option_symbol |
| underlying_close | DOUBLE | Underlying GME closing price | 28.50 | `data.close` from top-level JSON | CBOE data.close |
| cboe_timestamp | VARCHAR | Raw CBOE timestamp string | 2026-05-20T20:45:00-04:00 | `"timestamp"` from top-level JSON | CBOE timestamp |

### 6.2 DIM Layer

#### gme_dim_date

- **Materialization:** Table
- **Grain:** One row per calendar day
- **Refresh frequency:** Static (seeded once, covers 2024-01-01 to 2027-12-31)
- **Source:** `dim_date` seed CSV
- **Conformed:** Yes — reusable across any mart needing a trading calendar

| column_name | data_type | definition | example_value | calculation | data_source |
|-------------|-----------|-----------|---------------|-------------|-------------|
| date_key | INTEGER | Surrogate key in YYYYMMDD format | 20260520 | `date_key` | dim_date.csv |
| full_date | DATE | Calendar date | 2026-05-20 | `full_date` | dim_date.csv |
| year | INTEGER | Calendar year | 2026 | `year` | dim_date.csv |
| quarter | INTEGER | Calendar quarter (1–4) | 2 | `quarter` | dim_date.csv |
| month | INTEGER | Calendar month (1–12) | 5 | `month` | dim_date.csv |
| month_name | VARCHAR | Month name | May | `month_name` | dim_date.csv |
| day_of_week | INTEGER | Day of week (0=Sunday, 6=Saturday) | 3 | `day_of_week` | dim_date.csv |
| day_name | VARCHAR | Day name | Wednesday | `day_name` | dim_date.csv |
| is_weekend | BOOLEAN | Whether the date falls on a weekend | false | `is_weekend` | dim_date.csv |
| is_holiday | BOOLEAN | Whether the date is a US market holiday | false | `is_holiday` | dim_date.csv |
| is_trading_day | BOOLEAN | Whether US equity markets are open | true | `is_trading_day` | dim_date.csv |

### 6.3 DWD Layer

#### gme_dwd_option_contract_di

- **Source:** `gme_ods_cboe_options_chain`
- **Materialization:** Incremental
- **Incremental strategy:** `delete+insert` (dbt-duckdb; `merge` is not supported by this adapter)
- **Logical partition column:** `pull_date` (daily grain — inherits from ODS)
- **Unique key:** `['pull_date', 'option_symbol']`
- **Grain:** One row per option contract per pull date
- **Refresh frequency:** Daily
- **Filters applied:** `open_interest > 0 AND strike IS NOT NULL AND DTE >= 7`
- **Backfill protocol:** Set `--var backfill:true` to bypass the incremental date filter and reprocess all historical dates from ODS.
- **Restatement handling:** The `delete+insert` strategy on `(pull_date, option_symbol)` ensures that rerunning the same pull date replaces existing rows. Upstream ODS restatement propagates automatically on the next DWD run.

| column_name | data_type | definition | example_value | calculation | data_source |
|-------------|-----------|-----------|---------------|-------------|-------------|
| pull_date | DATE | Date of the options chain pull | 2026-05-20 | `ods.pull_date` | gme_ods_cboe_options_chain |
| ticker | VARCHAR | Underlying ticker | GME | `ods.ticker` | gme_ods_cboe_options_chain |
| expiry | DATE | Option expiration date | 2026-06-20 | `ods.expiry` | gme_ods_cboe_options_chain |
| strike | DOUBLE | Strike price | 25.0 | `ods.strike` | gme_ods_cboe_options_chain |
| option_type | VARCHAR | Call or put | call | `ods.option_type` | gme_ods_cboe_options_chain |
| option_symbol | VARCHAR | OCC contract identifier | GME260620C00025000 | `ods.option_symbol` | gme_ods_cboe_options_chain |
| bid | DOUBLE | Best bid price | 3.50 | `ods.bid` | gme_ods_cboe_options_chain |
| ask | DOUBLE | Best ask price | 3.80 | `ods.ask` | gme_ods_cboe_options_chain |
| mid_price | DOUBLE | Mid price with fallback | 3.65 | `CASE WHEN bid > 0 AND ask > 0 THEN (bid + ask) / 2.0 ELSE last_trade_price END` | Derived from ODS bid, ask, last_trade_price |
| last_trade_price | DOUBLE | Last traded price | 3.60 | `ods.last_trade_price` | gme_ods_cboe_options_chain |
| volume | INTEGER | Contracts traded (zero-coalesced) | 200 | `COALESCE(ods.volume, 0)` | gme_ods_cboe_options_chain |
| open_interest | INTEGER | Outstanding contracts (zero-coalesced) | 5000 | `COALESCE(ods.open_interest, 0)` | gme_ods_cboe_options_chain |
| implied_vol | DOUBLE | Implied volatility | 0.85 | `ods.iv` | gme_ods_cboe_options_chain |
| delta | DOUBLE | Option delta | 0.45 | `ods.delta` | gme_ods_cboe_options_chain |
| gamma | DOUBLE | Option gamma | 0.03 | `ods.gamma` | gme_ods_cboe_options_chain |
| theta | DOUBLE | Option theta | -0.05 | `ods.theta` | gme_ods_cboe_options_chain |
| vega | DOUBLE | Option vega | 0.12 | `ods.vega` | gme_ods_cboe_options_chain |
| rho | DOUBLE | Option rho | 0.02 | `ods.rho` | gme_ods_cboe_options_chain |
| theo | DOUBLE | Theoretical value | 3.65 | `ods.theo` | gme_ods_cboe_options_chain |
| dte | INTEGER | Days to expiry | 31 | `ods.expiry - ods.pull_date` | Derived from ODS expiry, pull_date |
| spot | DOUBLE | Underlying close price | 28.50 | `ods.underlying_close` | gme_ods_cboe_options_chain |
| gex_contribution | DOUBLE | Per-contract gamma exposure ($) | 12345.67 | `COALESCE(gamma, 0) * COALESCE(open_interest, 0) * 100 * POWER(underlying_close, 2) * 0.01 * CASE WHEN option_type = 'call' THEN 1 ELSE -1 END` | Derived from ODS gamma, OI, underlying_close, option_type |
| series_type | VARCHAR | Option series classification | MONTHLY | `CASE WHEN DTE > 365 THEN 'LEAP' WHEN DTE <= 7 THEN 'WEEKLY' ELSE 'MONTHLY' END` | Derived from DTE |
| provider | VARCHAR | Data provider | cboe | `ods.provider` | gme_ods_cboe_options_chain |
| pull_ts_utc | TIMESTAMP | Pull timestamp | 2026-05-20 20:45:00 | `ods.pull_ts_utc` | gme_ods_cboe_options_chain |
| cboe_timestamp | VARCHAR | Raw CBOE timestamp | 2026-05-20T20:45:00-04:00 | `ods.cboe_timestamp` | gme_ods_cboe_options_chain |

### 6.4 DWS Layer

#### gme_dws_strike_gex_1d

- **Materialization:** Table
- **Grain:** One row per strike per expiry per day
- **Refresh frequency:** Daily
- **Source:** `gme_dwd_option_contract_di`
- **Aggregation grain:** `GROUP BY pull_date, ticker, strike, expiry, dte, series_type`

| column_name | data_type | definition | example_value | calculation | data_source |
|-------------|-----------|-----------|---------------|-------------|-------------|
| pull_date | DATE | Pull date | 2026-05-20 | `pull_date` in `GROUP BY pull_date, ticker, strike, expiry, dte, series_type` | gme_dwd_option_contract_di |
| ticker | VARCHAR | Underlying ticker | GME | `ticker` in `GROUP BY pull_date, ticker, strike, expiry, dte, series_type` | gme_dwd_option_contract_di |
| strike | DOUBLE | Strike price | 25.0 | `strike` in `GROUP BY pull_date, ticker, strike, expiry, dte, series_type` | gme_dwd_option_contract_di |
| expiry | DATE | Expiration date | 2026-06-20 | `expiry` in `GROUP BY pull_date, ticker, strike, expiry, dte, series_type` | gme_dwd_option_contract_di |
| dte | INTEGER | Days to expiry | 31 | `dte` in `GROUP BY pull_date, ticker, strike, expiry, dte, series_type` | gme_dwd_option_contract_di |
| series_type | VARCHAR | WEEKLY / MONTHLY / LEAP | MONTHLY | `series_type` in `GROUP BY pull_date, ticker, strike, expiry, dte, series_type` | gme_dwd_option_contract_di |
| call_gex | DOUBLE | Total GEX from call contracts at this strike | 50000.00 | `SUM(CASE WHEN option_type = 'call' THEN gex_contribution ELSE 0 END)` | gme_dwd_option_contract_di |
| put_gex | DOUBLE | Total GEX from put contracts at this strike | -30000.00 | `SUM(CASE WHEN option_type = 'put' THEN gex_contribution ELSE 0 END)` | gme_dwd_option_contract_di |
| net_gex | DOUBLE | Net GEX at this strike (calls + puts) | 20000.00 | `SUM(gex_contribution)` | gme_dwd_option_contract_di |
| total_oi | BIGINT | Total open interest at this strike | 8500 | `SUM(open_interest)` | gme_dwd_option_contract_di |
| avg_iv | DOUBLE | Average implied volatility at this strike | 0.82 | `AVG(implied_vol)` | gme_dwd_option_contract_di |
| gex_rank | INTEGER | Rank by absolute net GEX within the day (1 = highest) | 3 | `ROW_NUMBER() OVER (PARTITION BY pull_date, ticker ORDER BY ABS(SUM(gex_contribution)) DESC)` | Derived |

#### gme_dws_daily_snapshot_1d

- **Materialization:** Table
- **Grain:** One row per day
- **Refresh frequency:** Daily
- **Sources:** `gme_dwd_option_contract_di`, `gme_dws_strike_gex_1d`

| column_name | data_type | definition | example_value | calculation | data_source |
|-------------|-----------|-----------|---------------|-------------|-------------|
| pull_date | DATE | Pull date | 2026-05-20 | `DISTINCT pull_date` from DWD | gme_dwd_option_contract_di |
| ticker | VARCHAR | Underlying ticker | GME | From DWD | gme_dwd_option_contract_di |
| spot | DOUBLE | Underlying close price | 28.50 | `DISTINCT spot` from DWD | gme_dwd_option_contract_di |
| max_pain_strike | DOUBLE | Strike minimizing total exercise pain | 27.00 | Cross-join DWD contracts; for each candidate strike, `SUM(CASE WHEN c2.option_type = 'call' AND c2.strike < c1.strike THEN (c1.strike - c2.strike) * c2.open_interest * 100 WHEN c2.option_type = 'put' AND c2.strike > c1.strike THEN (c2.strike - c1.strike) * c2.open_interest * 100 ELSE 0 END)`; select candidate with `MIN(total_pain)` via `QUALIFY ROW_NUMBER() OVER (ORDER BY total_pain ASC) = 1` | gme_dwd_option_contract_di |
| max_pain_convergence_pct | DOUBLE | Spot-to-max-pain distance as % | 5.26 | `ROUND(ABS(spot - max_pain_strike) / spot * 100, 2)` | Derived from spot and max_pain_strike |
| net_gex | DOUBLE | Total net GEX across all strikes | 150000.00 | `SUM(net_gex)` from strike_gex_1d | gme_dws_strike_gex_1d |
| top_gex_strike | DOUBLE | Strike with highest absolute net GEX | 30.00 | `SELECT strike FROM strike_gex_1d ORDER BY ABS(net_gex) DESC LIMIT 1` | gme_dws_strike_gex_1d |
| pc_ratio | DOUBLE | Put/call open interest ratio | 0.85 | `SUM(CASE WHEN option_type = 'put' THEN open_interest ELSE 0 END) * 1.0 / NULLIF(SUM(CASE WHEN option_type = 'call' THEN open_interest ELSE 0 END), 0)` | gme_dwd_option_contract_di |
| top_oi_strike_1 | DOUBLE | Strike with highest total OI | 30.00 | `SUM(open_interest) GROUP BY strike`, ranked `ROW_NUMBER() ORDER BY open_interest DESC`, `oi_rank = 1` | gme_dwd_option_contract_di |
| top_oi_strike_2 | DOUBLE | Strike with 2nd highest total OI | 25.00 | Same as above, `oi_rank = 2` | gme_dwd_option_contract_di |
| top_oi_strike_3 | DOUBLE | Strike with 3rd highest total OI | 35.00 | Same as above, `oi_rank = 3` | gme_dwd_option_contract_di |

#### gme_dws_options_metrics_1d

- **Materialization:** Table
- **Grain:** One row per pull_date (single-ticker GME)
- **Refresh frequency:** Daily
- **Sources:** `gme_dws_strike_gex_1d`, `gme_dwd_option_contract_di`, `gme_underlying_closes` (seed)

| column_name | data_type | definition | example_value | calculation | data_source |
|-------------|-----------|-----------|---------------|-------------|-------------|
| pull_date | DATE | Pull date | 2026-05-20 | `DISTINCT pull_date` from DWD | gme_dwd_option_contract_di |
| ticker | VARCHAR | Underlying ticker | GME | From DWD | gme_dwd_option_contract_di |
| gamma_flip_point | DOUBLE | Price where cumulative net GEX crosses zero | 29.50 | Cumulative sum of `net_gex_at_strike` ordered by strike; linear interpolation at zero-crossing: `strike + (0 - cum_gex) / NULLIF(next_cum_gex - cum_gex, 0) * (next_strike - strike)` where `(cum_gex >= 0 AND next_cum_gex < 0) OR (cum_gex < 0 AND next_cum_gex >= 0)`; fallback: strike with `MIN(ABS(cum_gex))` if no crossing found; rounded to 2 decimal places | gme_dws_strike_gex_1d (aggregated by strike) |
| iv30 | DOUBLE | OI-weighted average IV for 20–40 DTE contracts | 0.8500 | `ROUND(SUM(implied_vol * open_interest) * 1.0 / NULLIF(SUM(open_interest), 0), 4)` WHERE `dte BETWEEN 20 AND 40 AND implied_vol IS NOT NULL` | gme_dwd_option_contract_di |
| hv20 | DOUBLE | 20-day annualized historical volatility | 0.6200 | `ROUND(STDDEV(LN(close_price / LAG(close_price))) * SQRT(252), 4)` over `ROWS BETWEEN 20 PRECEDING AND CURRENT ROW` where `COUNT(log_return) >= 20`; joined to pull_date via `MAX(trade_date) WHERE trade_date <= pull_date AND hv20 IS NOT NULL` | gme_underlying_closes (seed) |
| iv_rank | DOUBLE | IV30 rank within 252-session lookback | 0.7500 | `ROUND((iv30 - min_iv30_252d) / NULLIF(max_iv30_252d - min_iv30_252d, 0), 4)` where 252-session window uses self-join on `session_num BETWEEN session_num - 251 AND session_num`; NULL if `iv30_day_count < 20` | Derived from iv30 history |
| oi_daily_delta | BIGINT | Change in total OI from previous day | 1500 | `SUM(open_interest) - LAG(SUM(open_interest)) OVER (PARTITION BY ticker ORDER BY pull_date)`; NULL on first observation | gme_dwd_option_contract_di |
| dealer_net_gamma | DOUBLE | Total dealer gamma exposure | 250000.00 | `ROUND(SUM(gex_contribution), 2)` across all contracts for the day | gme_dwd_option_contract_di |
| iv_percentile | DOUBLE | Fraction of 252 sessions where IV30 was lower | 0.8200 | `ROUND(days_below * 1.0 / NULLIF(iv30_day_count, 0), 4)` where `days_below = SUM(CASE WHEN prior_iv30 < current_iv30 THEN 1 ELSE 0 END)` over 252-session window; NULL if `iv30_day_count < 20` | Derived from iv30 history |

#### gme_dws_social_sentiment_1d

- **Materialization:** Table
- **Grain:** One row per ticker per day
- **Refresh frequency:** Daily
- **Source:** `gme_social_sentiment` (seed)
- **Provenance:** Fixture-only — this model reads from a static seed CSV with no live data provider. The seed contains illustrative social sentiment aggregates for CI/demo purposes. There is no ODS ingestion layer, no live API, and no operator-facing claim of real-time or historical accuracy. If a live social sentiment source is added in the future, an ODS provenance layer with source URL, capture timestamp, and provider attribution must be introduced before the data can be presented as operational.

| column_name | data_type | definition | example_value | calculation | data_source |
|-------------|-----------|-----------|---------------|-------------|-------------|
| pull_date | DATE | Observation date (aliased from observed_date) | 2026-05-16 | `observed_date AS pull_date` | gme_social_sentiment (seed) |
| ticker | VARCHAR | Underlying ticker | GME | `ticker` in `GROUP BY observed_date, ticker` | gme_social_sentiment (seed) |
| social_mention_count | BIGINT | Total social media mentions for the day | 150 | `SUM(mention_count)` | gme_social_sentiment (seed) |
| social_sentiment_score | DOUBLE | Mention-weighted average sentiment (−1 to +1) | 0.3200 | `ROUND(SUM(sentiment_score * mention_count) / NULLIF(SUM(mention_count), 0), 4)` | gme_social_sentiment (seed) |

### 6.5 ADS Layer

#### gme_ads_market_dashboard

- **Materialization:** Table
- **Grain:** One row per day
- **Refresh frequency:** Daily
- **Sources:** Left-outer join of all DWS models + dim_date
- **Purpose:** One-big-table (OBT) for Streamlit dashboard consumption

| column_name | data_type | definition | example_value | calculation | data_source |
|-------------|-----------|-----------|---------------|-------------|-------------|
| pull_date | DATE | Pull date (join key to all DWS + dim) | 2026-05-20 | `sn.pull_date` | gme_dws_daily_snapshot_1d |
| ticker | VARCHAR | Underlying ticker | GME | `sn.ticker` | gme_dws_daily_snapshot_1d |
| spot | DOUBLE | Underlying close price | 28.50 | `sn.spot` | gme_dws_daily_snapshot_1d |
| year | INTEGER | Calendar year | 2026 | `d.year` | gme_dim_date |
| quarter | INTEGER | Calendar quarter | 2 | `d.quarter` | gme_dim_date |
| month_name | VARCHAR | Month name | May | `d.month_name` | gme_dim_date |
| day_name | VARCHAR | Day name | Wednesday | `d.day_name` | gme_dim_date |
| is_trading_day | BOOLEAN | Whether markets were open | true | `d.is_trading_day` | gme_dim_date |
| max_pain_strike | DOUBLE | Max pain strike | 27.00 | `sn.max_pain_strike` | gme_dws_daily_snapshot_1d |
| max_pain_convergence_pct | DOUBLE | Spot-to-max-pain distance % | 5.26 | `sn.max_pain_convergence_pct` | gme_dws_daily_snapshot_1d |
| net_gex | DOUBLE | Total net GEX | 150000.00 | `sn.net_gex` | gme_dws_daily_snapshot_1d |
| top_gex_strike | DOUBLE | Strike with highest absolute GEX | 30.00 | `sn.top_gex_strike` | gme_dws_daily_snapshot_1d |
| pc_ratio | DOUBLE | Put/call OI ratio | 0.85 | `sn.pc_ratio` | gme_dws_daily_snapshot_1d |
| top_oi_strike_1 | DOUBLE | Highest OI strike | 30.00 | `sn.top_oi_strike_1` | gme_dws_daily_snapshot_1d |
| top_oi_strike_2 | DOUBLE | 2nd highest OI strike | 25.00 | `sn.top_oi_strike_2` | gme_dws_daily_snapshot_1d |
| top_oi_strike_3 | DOUBLE | 3rd highest OI strike | 35.00 | `sn.top_oi_strike_3` | gme_dws_daily_snapshot_1d |
| gamma_flip_point | DOUBLE | Gamma flip price | 29.50 | `m.gamma_flip_point` | gme_dws_options_metrics_1d |
| iv30 | DOUBLE | 30-day implied volatility | 0.8500 | `m.iv30` | gme_dws_options_metrics_1d |
| hv20 | DOUBLE | 20-day historical volatility | 0.6200 | `m.hv20` | gme_dws_options_metrics_1d |
| iv_rank | DOUBLE | IV rank (252-session) | 0.7500 | `m.iv_rank` | gme_dws_options_metrics_1d |
| oi_daily_delta | BIGINT | Daily change in total OI | 1500 | `m.oi_daily_delta` | gme_dws_options_metrics_1d |
| dealer_net_gamma | DOUBLE | Dealer net gamma exposure | 250000.00 | `m.dealer_net_gamma` | gme_dws_options_metrics_1d |
| iv_percentile | DOUBLE | IV percentile (252-session) | 0.8200 | `m.iv_percentile` | gme_dws_options_metrics_1d |
| social_mention_count | BIGINT | Social media mentions | 150 | `ss.social_mention_count` | gme_dws_social_sentiment_1d |
| social_sentiment_score | DOUBLE | Weighted sentiment score | 0.3200 | `ss.social_sentiment_score` | gme_dws_social_sentiment_1d |

### 6.6 Seed Tables

#### dim_date (seed)

| column_name | data_type | definition | example_value | calculation | data_source |
|-------------|-----------|-----------|---------------|-------------|-------------|
| date_key | INTEGER | YYYYMMDD surrogate key | 20260520 | `date_key` | dim_date.csv |
| full_date | DATE | Calendar date | 2026-05-20 | `full_date` | dim_date.csv |
| year | INTEGER | Year | 2026 | `year` | dim_date.csv |
| quarter | INTEGER | Quarter (1–4) | 2 | `quarter` | dim_date.csv |
| month | INTEGER | Month (1–12) | 5 | `month` | dim_date.csv |
| month_name | VARCHAR | Month name | May | `month_name` | dim_date.csv |
| day_of_week | INTEGER | Day of week (0–6) | 3 | `day_of_week` | dim_date.csv |
| day_name | VARCHAR | Day name | Wednesday | `day_name` | dim_date.csv |
| is_weekend | BOOLEAN | Weekend flag | false | `is_weekend` | dim_date.csv |
| is_holiday | BOOLEAN | Holiday flag | false | `is_holiday` | dim_date.csv |
| is_trading_day | BOOLEAN | Trading day flag | true | `is_trading_day` | dim_date.csv |

#### gme_underlying_closes (seed)

| column_name | data_type | definition | example_value | calculation | data_source |
|-------------|-----------|-----------|---------------|-------------|-------------|
| trade_date | DATE | Trading date | 2026-05-20 | `trade_date` | gme_underlying_closes.csv |
| ticker | VARCHAR | Ticker symbol | GME | `ticker` | gme_underlying_closes.csv |
| close_price | DOUBLE | Daily closing price | 28.50 | `close_price` | gme_underlying_closes.csv |

#### gme_social_sentiment (seed)

| column_name | data_type | definition | example_value | calculation | data_source |
|-------------|-----------|-----------|---------------|-------------|-------------|
| observed_date | DATE | Observation date | 2026-05-16 | `observed_date` | gme_social_sentiment.csv |
| ticker | VARCHAR | Ticker symbol | GME | `ticker` | gme_social_sentiment.csv |
| source | VARCHAR | Aggregated social source label | social_aggregate | `source` | gme_social_sentiment.csv |
| mention_count | INTEGER | Number of mentions | 1567 | `mention_count` | gme_social_sentiment.csv |
| sentiment_score | DOUBLE | Sentiment score (−1 to +1) | 0.21 | `sentiment_score` | gme_social_sentiment.csv |
| source_url | VARCHAR | Public reference URL for the aggregate | https://finance.yahoo.com/quote/GME/community | `source_url` | gme_social_sentiment.csv |

---

## 6.7 ODS/DWD Refresh Semantics Summary

All incremental models in this mart use the `delete+insert` strategy, the only
merge-capable strategy supported by dbt-duckdb. The `merge` strategy used by
dbt-postgres/dbt-snowflake is **not available** in dbt-duckdb.

| Model | Strategy | Unique Key | Partition | Backfill Var | Restatement |
|-------|----------|-----------|-----------|--------------|-------------|
| gme_ods_cboe_options_chain | `delete+insert` | `[pull_date, option_symbol]` | `pull_date` | `--var backfill:true` | Same-day rerun replaces rows; idempotent |
| gme_dwd_option_contract_di | `delete+insert` | `[pull_date, option_symbol]` | `pull_date` | `--var backfill:true` | Same-day rerun replaces rows; upstream restatement propagates on next run |

**Idempotence guarantee:** Running `dbt build` twice with the same source data
produces identical row counts. The `delete+insert` strategy deletes all existing
rows matching the incoming `unique_key` values before inserting, so duplicate
appends are structurally impossible.

**Fixture mode (`use_fixture: true`):** The ODS reads a static Parquet snapshot.
On rerun, `delete+insert` removes the prior load and re-inserts the same rows.
Row count is stable across runs.

**Live mode (`use_fixture: false`):** The incremental filter
(`WHERE pull_date >= MAX(prior pull_date)`) limits ingestion to new trading days.
If the same day is re-pulled, `delete+insert` replaces the prior snapshot.

### Social Sentiment Provenance

`gme_dws_social_sentiment_1d` is a **fixture-only exception**. It reads directly
from the `gme_social_sentiment` seed CSV with no ODS ingestion layer and no live
data provider. The seed contains illustrative aggregates for CI and demo
purposes only. No live or operator-facing accuracy claim is made.

If a live social sentiment source is integrated in the future, an ODS provenance
layer must be introduced with: source URL, capture timestamp, provider
attribution, and the same `delete+insert` incremental semantics documented above.

---

## 7. DQC Plan

### 7.1 Control Catalog

| # | Control Class | Test | Target Model(s) | Tolerance | Severity | Test File |
|---|---------------|------|-----------------|-----------|----------|-----------|
| 1 | PK Integrity | `not_null` + `unique` on date_key (DIM), pull_date (DWS/ADS) | gme_dim_date, gme_dws_daily_snapshot_1d, gme_dws_options_metrics_1d, gme_dws_social_sentiment_1d, gme_ads_market_dashboard | 0 | error | models/schema.yml |
| 2 | FK Integrity | ADS pull_date → gme_dim_date.full_date relationship | gme_ads_market_dashboard | 0 | error | models/schema.yml |
| 3 | Freshness | `pull_ts_utc IS NOT NULL` on all ODS rows | gme_ods_cboe_options_chain | 0 | error | tests/test_dqc_freshness.sql |
| 4 | Completeness | Minimum row counts: fixture mode ODS≥5, DWD≥5, DWS strike≥3, DWS snapshot≥1; live mode ODS≥100, DWD≥50, DWS≥10, snapshot≥1 | gme_ods_cboe_options_chain, gme_dwd_option_contract_di, gme_dws_strike_gex_1d, gme_dws_daily_snapshot_1d | 0 | error | tests/test_dqc_completeness.sql |
| 5 | Accepted Ranges | strike > 0, open_interest ≥ 0 (DWD); spot > 0, pc_ratio ∈ [0, 50] (DWS) | gme_dwd_option_contract_di, gme_dws_daily_snapshot_1d | 0 | error | tests/test_dqc_accepted_ranges.sql |
| 6 | Duplicate Detection | No duplicate (pull_date, option_symbol) | gme_dwd_option_contract_di | 0 | error | tests/test_dqc_duplicate_detection.sql |
| 7 | Null-Rate | Greeks (implied_vol, delta, gamma, mid_price) null rate < 5% | gme_dwd_option_contract_di | 5% | warn | tests/test_dqc_null_rate.sql |
| 8 | Business Reconciliation | DWD row count ≤ ODS row count (proxy); GEX vs external waived | gme_dwd_option_contract_di, gme_ods_cboe_options_chain | 0.5 | warn | tests/test_dqc_reconciliation.sql |
| 9 | Rerun Idempotence | No duplicate `(pull_date, option_symbol)` in ODS after repeated runs; proves `delete+insert` prevents row doubling | gme_ods_cboe_options_chain | 0 | error | tests/test_ods_incremental_history.sql |
| 10 | Rerun Idempotence | No duplicate `(pull_date, option_symbol)` in DWD after repeated runs | gme_dwd_option_contract_di | 0 | error | tests/test_dwd_incremental_idempotence.sql |

### 7.2 Additional Schema Tests (models/schema.yml)

| Model | Column | Test |
|-------|--------|------|
| gme_ods_cboe_options_chain | option_symbol, pull_date, ticker, provider, pull_ts_utc, quote_ts_utc, run_id | not_null |
| gme_ods_cboe_options_chain | provider | accepted_values: [cboe] |
| gme_ods_cboe_options_chain | ticker | accepted_values: [GME] |
| gme_ods_cboe_options_chain | strike | not_null (severity: warn) |
| gme_dim_date | date_key, full_date | not_null + unique |
| gme_dim_date | is_trading_day | not_null |
| gme_dwd_option_contract_di | option_symbol, pull_date, strike, expiry, option_type, open_interest, gex_contribution, series_type | not_null |
| gme_dwd_option_contract_di | option_type | accepted_values: [call, put] |
| gme_dwd_option_contract_di | series_type | accepted_values: [WEEKLY, MONTHLY, LEAP] |
| gme_dws_strike_gex_1d | pull_date, strike, net_gex, gex_rank | not_null |
| gme_dws_daily_snapshot_1d | pull_date | not_null + unique |
| gme_dws_daily_snapshot_1d | spot, pc_ratio | not_null |
| gme_dws_options_metrics_1d | pull_date | not_null + unique |
| gme_dws_options_metrics_1d | ticker | not_null, accepted_values: [GME] |
| gme_dws_social_sentiment_1d | pull_date | not_null + unique |
| gme_dws_social_sentiment_1d | ticker | not_null, accepted_values: [GME] |
| gme_ads_market_dashboard | pull_date | not_null + unique |
| gme_ads_market_dashboard | pull_date | relationships → gme_dim_date.full_date |
| gme_ads_market_dashboard | spot, ticker, gamma_flip_point, iv30, dealer_net_gamma | not_null |

### 7.3 Scorecard Artifact

- **File:** `dqc_scorecard.json`
- **Format:** Machine-readable JSON with per-control status, attempt history, evidence, and rollup score
- **Dashboard integration:** Streamlit app reads the scorecard and displays a DQC status badge (PASS / PARTIAL / WAIVERS / UNKNOWN / FAIL)

---

## 8. Job Monitoring

### Pipeline Execution

```bash
cd examples/gme-options-mart
dbt seed --profiles-dir .
dbt run --profiles-dir .
dbt test --profiles-dir .
```

### CI Expectations

- **GitHub Actions:** All three commands (`seed`, `run`, `test`) must pass on every PR
- **Fail-fast:** Pipeline halts on first failure (no partial runs)
- **Timeout:** 10 minutes maximum per pipeline execution
- **Fixture mode:** CI always runs with `use_fixture: true` for deterministic results

### Dashboard Launch

```bash
pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py
```

### Cron Schedule (Production)

```
45 20 * * 1-5  America/New_York
```

Runs at 8:45 PM ET on weekdays, after US market close. Skips weekends and holidays (checked via `is_trading_day` in dim_date).

---

## 9. Bidirectional Traceability

### 9.1 ADS Columns → Source Models

Every column in `gme_ads_market_dashboard` traces to exactly one DWS model or dimension:

| ADS Column | Source Model | Source Column |
|------------|-------------|---------------|
| pull_date | gme_dws_daily_snapshot_1d | pull_date |
| ticker | gme_dws_daily_snapshot_1d | ticker |
| spot | gme_dws_daily_snapshot_1d | spot |
| year | gme_dim_date | year |
| quarter | gme_dim_date | quarter |
| month_name | gme_dim_date | month_name |
| day_name | gme_dim_date | day_name |
| is_trading_day | gme_dim_date | is_trading_day |
| max_pain_strike | gme_dws_daily_snapshot_1d | max_pain_strike |
| max_pain_convergence_pct | gme_dws_daily_snapshot_1d | max_pain_convergence_pct |
| net_gex | gme_dws_daily_snapshot_1d | net_gex |
| top_gex_strike | gme_dws_daily_snapshot_1d | top_gex_strike |
| pc_ratio | gme_dws_daily_snapshot_1d | pc_ratio |
| top_oi_strike_1 | gme_dws_daily_snapshot_1d | top_oi_strike_1 |
| top_oi_strike_2 | gme_dws_daily_snapshot_1d | top_oi_strike_2 |
| top_oi_strike_3 | gme_dws_daily_snapshot_1d | top_oi_strike_3 |
| gamma_flip_point | gme_dws_options_metrics_1d | gamma_flip_point |
| iv30 | gme_dws_options_metrics_1d | iv30 |
| hv20 | gme_dws_options_metrics_1d | hv20 |
| iv_rank | gme_dws_options_metrics_1d | iv_rank |
| oi_daily_delta | gme_dws_options_metrics_1d | oi_daily_delta |
| dealer_net_gamma | gme_dws_options_metrics_1d | dealer_net_gamma |
| iv_percentile | gme_dws_options_metrics_1d | iv_percentile |
| social_mention_count | gme_dws_social_sentiment_1d | social_mention_count |
| social_sentiment_score | gme_dws_social_sentiment_1d | social_sentiment_score |

### 9.2 TDD Metric → SQL Model → DQC Test

| Metric | TDD Section | Model File | DQC Test |
|--------|-------------|-----------|----------|
| gex_contribution | 6.3 DWD | models/dwd/gme_dwd_option_contract_di.sql | schema.yml: not_null |
| call_gex, put_gex, net_gex | 6.4 DWS strike_gex | models/dws/gme_dws_strike_gex_1d.sql | schema.yml: not_null on net_gex |
| gex_rank | 6.4 DWS strike_gex | models/dws/gme_dws_strike_gex_1d.sql | schema.yml: not_null |
| net_gex (total) | 6.4 DWS snapshot | models/dws/gme_dws_daily_snapshot_1d.sql | Aggregated from tested source |
| top_gex_strike | 6.4 DWS snapshot | models/dws/gme_dws_daily_snapshot_1d.sql | Covered by DWS source tests and ADS dashboard review |
| max_pain_strike | 6.4 DWS snapshot | models/dws/gme_dws_daily_snapshot_1d.sql | Covered by DWS source tests and public fact-check link |
| max_pain_convergence_pct | 6.4 DWS snapshot | models/dws/gme_dws_daily_snapshot_1d.sql | Covered by DWS source tests and ADS dashboard review |
| pc_ratio | 6.4 DWS snapshot | models/dws/gme_dws_daily_snapshot_1d.sql | schema.yml: not_null; test_dqc_accepted_ranges |
| top_oi_strike_1/2/3 | 6.4 DWS snapshot | models/dws/gme_dws_daily_snapshot_1d.sql | Covered by DWS source tests and public fact-check link |
| gamma_flip_point | 6.4 DWS metrics | models/dws/gme_dws_options_metrics_1d.sql | schema.yml: not_null (ADS) |
| iv30 | 6.4 DWS metrics | models/dws/gme_dws_options_metrics_1d.sql | schema.yml: not_null (ADS) |
| hv20 | 6.4 DWS metrics | models/dws/gme_dws_options_metrics_1d.sql | Covered by DWS source tests and ADS dashboard review |
| iv_rank | 6.4 DWS metrics | models/dws/gme_dws_options_metrics_1d.sql | Covered by DWS source tests and ADS dashboard review |
| oi_daily_delta | 6.4 DWS metrics | models/dws/gme_dws_options_metrics_1d.sql | Covered by DWS source tests and ADS dashboard review |
| dealer_net_gamma | 6.4 DWS metrics | models/dws/gme_dws_options_metrics_1d.sql | schema.yml: not_null (ADS) |
| iv_percentile | 6.4 DWS metrics | models/dws/gme_dws_options_metrics_1d.sql | Covered by DWS source tests and ADS dashboard review |
| social_mention_count | 6.4 DWS sentiment | models/dws/gme_dws_social_sentiment_1d.sql | schema.yml: not_null |
| social_sentiment_score | 6.4 DWS sentiment | models/dws/gme_dws_social_sentiment_1d.sql | Covered by DWS source tests and ADS dashboard review |
| mid_price | 6.3 DWD | models/dwd/gme_dwd_option_contract_di.sql | Covered by DWD source tests and DQC null-rate test |
| dte | 6.3 DWD | models/dwd/gme_dwd_option_contract_di.sql | Covered by DWD source tests and DTE filter in DWD model |
| series_type | 6.3 DWD | models/dwd/gme_dwd_option_contract_di.sql | schema.yml: accepted_values |
| expiry (parsed) | 6.1 ODS | models/ods/gme_ods_cboe_options_chain.sql | Covered by DWD DTE filter and DWD source tests |
| option_type (parsed) | 6.1 ODS | models/ods/gme_ods_cboe_options_chain.sql | schema.yml: accepted_values |
| strike (parsed) | 6.1 ODS | models/ods/gme_ods_cboe_options_chain.sql | schema.yml: not_null (warn) |

---

## 10. Sign-Off

| Role | Name | Responsibility | Date | Status |
|------|------|----------------|------|--------|
| Tech lead / designer | (open-source example) | Technical design owner | 2026-05-23 | approved |
| Reviewer | (community) | Public example reviewer | 2026-05-23 | approved |
