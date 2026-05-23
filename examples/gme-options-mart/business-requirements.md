# Business Requirements Document: GME Options Mart

> Version 1.1 — Open-source example for the mart-forge framework.
>
> V1.1 (2026-05-23): Consolidated metric-source contract with source-native disposition policy. Replaced stale Appendix A with browser-verified evidence matching §2.8. Added ChartExchange comparator, rejected broken/wrong-asset links.

---

## 1. Business Process

The GME Options Mart tracks the **options market microstructure** for GameStop Corp (NYSE: GME). The core business process is the daily capture and analysis of options chain data — open interest, Greeks, implied volatility, and derived exposure metrics — to produce a consolidated analytical view of market positioning.

This mart serves as the canonical advanced example for the mart-forge framework, demonstrating that the methodology handles real-world financial data with complex derived metrics (GEX, max pain, IV rank) and multi-source ingestion (CBOE options, Yahoo Finance underlying closes, social sentiment).

### Business Questions This Mart Answers

1. **What is the current gamma exposure (GEX) profile?** — Where are dealers positioned, what is the net gamma, and at which strike is GEX concentrated?
2. **Where is the max pain strike relative to spot?** — How close is the underlying price to the point of maximum option holder loss?
3. **Is sentiment bullish or bearish?** — What does the put/call ratio indicate? What does social sentiment suggest?
4. **How volatile is the underlying relative to history?** — What is the current IV30 vs. HV20? Where does IV rank among the last 252 sessions?
5. **How is open interest changing?** — Is OI expanding (new positions being opened) or contracting (positions being closed)?
6. **What is the gamma flip point?** — At what price does the net cumulative GEX cross zero, indicating a shift from positive to negative gamma territory?

---

## 2. Metrics Catalog

### 2.1 Core Options Chain Metrics (from CBOE)

| Metric | Definition | Unit | Source |
|--------|-----------|------|--------|
| bid / ask | Best bid and ask prices for the option contract | USD | CBOE delayed quotes |
| mid_price | Midpoint of bid/ask; falls back to last_trade_price when bid or ask is zero | USD | Derived from CBOE |
| implied_vol (IV) | CBOE-computed implied volatility for the contract | Decimal (0–1+) | CBOE delayed quotes |
| delta | Rate of change of option price relative to underlying price | Decimal (-1 to 1) | CBOE delayed quotes |
| gamma | Rate of change of delta relative to underlying price | Decimal | CBOE delayed quotes |
| theta | Rate of option price decay per day | USD/day | CBOE delayed quotes |
| vega | Sensitivity of option price to 1% change in IV | USD/1% | CBOE delayed quotes |
| rho | Sensitivity of option price to interest rate changes | USD/1% | CBOE delayed quotes |
| open_interest | Number of outstanding option contracts | Contracts | CBOE delayed quotes |
| volume | Number of contracts traded on the pull date | Contracts | CBOE delayed quotes |

### 2.2 Derived GEX Metrics

| Metric | Definition | Formula | Layer |
|--------|-----------|---------|-------|
| gex_contribution | Per-contract gamma exposure in dollar terms | `gamma * OI * 100 * spot² * 0.01 * sign(call=+1, put=-1)` | DWD |
| call_gex | Aggregate GEX from call contracts at a given strike | `SUM(gex_contribution WHERE option_type = 'call')` | DWS |
| put_gex | Aggregate GEX from put contracts at a given strike | `SUM(gex_contribution WHERE option_type = 'put')` | DWS |
| net_gex (strike) | Net GEX at a specific strike (calls + puts) | `SUM(gex_contribution)` per strike | DWS |
| net_gex (daily) | Total net GEX across all strikes for the day | `SUM(net_gex)` across all strikes | DWS |
| top_gex_strike | Strike with the highest absolute net GEX | Strike at `MAX(ABS(net_gex))` | DWS |
| gex_rank | Rank of each strike by absolute net GEX within a day | `ROW_NUMBER() ORDER BY ABS(net_gex) DESC` | DWS |
| gamma_flip_point | Price where cumulative net GEX crosses zero (linear interpolation) | Interpolated zero-crossing of cumulative GEX curve; fallback: nearest-to-zero strike | DWS |
| dealer_net_gamma | Total dealer gamma exposure (sum of all per-contract GEX) | `SUM(gex_contribution)` across all contracts | DWS |

### 2.3 Max Pain and Positioning Metrics

| Metric | Definition | Formula | Layer |
|--------|-----------|---------|-------|
| max_pain_strike | Strike minimizing total exercise value for option holders | Cross-join pain calc: MIN of (ITM call pain + ITM put pain) across candidate strikes | DWS |
| max_pain_convergence_pct | How far spot is from max pain, as a percentage | `ABS(spot - max_pain_strike) / spot * 100` | DWS |
| pc_ratio | Put/call open interest ratio | `SUM(put_OI) / SUM(call_OI)` | DWS |
| top_oi_strike_1/2/3 | Top three strikes ranked by total open interest | `ROW_NUMBER() ORDER BY SUM(OI) DESC` | DWS |

### 2.4 Implied Volatility Metrics

| Metric | Definition | Formula | Layer |
|--------|-----------|---------|-------|
| iv30 | OI-weighted average IV for near-30-DTE contracts (20–40 DTE window) | `SUM(IV * OI) / SUM(OI)` for DTE ∈ [20, 40] | DWS |
| iv_rank | Percentile rank of current IV30 within a 252-session lookback | `(current_iv30 - min_iv30_252d) / (max_iv30_252d - min_iv30_252d)` | DWS |
| iv_percentile | Fraction of 252 sessions where historical IV30 was below current IV30 | `days_below / iv30_day_count` | DWS |

### 2.5 Historical Volatility and OI Metrics

| Metric | Definition | Formula | Layer |
|--------|-----------|---------|-------|
| hv20 | 20-day annualized historical volatility of the underlying | `STDDEV(LN(close/prev_close)) * SQRT(252)` over 20 log-returns | DWS |
| oi_daily_delta | Change in total open interest from previous trading day | `total_oi(today) - LAG(total_oi)` | DWS |

### 2.6 Social Sentiment Metrics

| Metric | Definition | Formula | Layer |
|--------|-----------|---------|-------|
| social_mention_count | Total social media mentions for GME on a given day | `SUM(mention_count)` | DWS |
| social_sentiment_score | Mention-weighted average sentiment score (−1 to +1) | `SUM(sentiment_score * mention_count) / SUM(mention_count)` | DWS |

> **Note:** `social_mention_count` and `social_sentiment_score` use seed fixture data for CI. No free live API provides a mention-weighted score matching this mart's exact definition. `social_sentiment_score` is marked **unsupported** for live fact-check comparison; see Section 2.7.

### 2.7 Metric-Source Contract

Each dashboard metric is classified by its data origin. This contract ensures the dashboard never misrepresents a model-derived value as a provider-reported number.

| Classification | Definition |
|---------------|-----------|
| **source_native** | Value read directly from the upstream provider (CBOE) and displayed as-is. No mart-side calculation — the provider computes and reports the value. |
| **derived** | Computed by dbt models from source-native inputs. Formula is documented in TDD/BRD. Used when the provider does not report the metric directly or when the mart requires a specific calculation methodology (e.g. per-expiry/per-class scoping). |
| **comparator_only** | External reference link for manual comparison. The mart does not ingest from this source; it is a link only. |
| **unsupported** | No viable free live source exists. Value uses seed fixture for CI only. |

**Source-native vs derived disposition policy:** A metric is classified `source_native` only when the upstream provider (CBOE) reports the value directly in its payload and the mart displays it without transformation. All other metrics are `derived` — even when an external comparator site shows a similar number, the mart computes its own value from CBOE inputs using documented formulas. If a future provider reports a metric directly (e.g. CBOE adding a GEX field), the classification may be upgraded to `source_native` after verifying the provider's methodology matches the mart's definition. Metrics where provider-reported and mart-derived values coexist should document both and note which is displayed.

| Dashboard Card | Metric | Source Type | Provider / Formula | Expiry Grain | Contract Class | Freshness | Dashboard Label |
|----------------|--------|-------------|-------------------|-------------|---------------|-----------|----------------|
| Spot Price | spot | source_native | CBOE `underlying_close` | — | — | 15-min delayed | CBOE source |
| Max Pain | max_pain_strike | derived | Cross-join pain calc on distinct strike candidates | per-expiry (nearest standard shown) | standard only | as-of pull_date | model-derived |
| Max Pain Convergence | max_pain_convergence_pct | derived | `ABS(spot - max_pain) / spot * 100` | per-expiry | standard only | as-of pull_date | model-derived |
| P/C Ratio | pc_ratio | derived | `SUM(put_OI) / SUM(call_OI)` for nearest standard expiry | per-expiry (nearest standard shown) | standard only | as-of pull_date | model-derived |
| Net GEX | net_gex | derived | `SUM(gamma * OI * 100 * spot^2 * 0.01 * sign)` | all | all | as-of pull_date | model-derived |
| IV30 | iv30 | derived | OI-weighted avg IV for 20-40 DTE window | 20-40 DTE | all | as-of pull_date | model-derived |
| HV20 | hv20 | derived | `STDDEV(LN(close/prev)) * SQRT(252)` over 20 returns | — | — | latest seed close | model-derived |
| Gamma Flip | gamma_flip_point | derived | Zero-crossing of cumulative net GEX curve | all | all | as-of pull_date | model-derived |
| IV Rank | iv_rank | derived | `(iv30 - min_252d) / (max_252d - min_252d)` | — | — | 252-session window | model-derived |
| IV Percentile | iv_percentile | derived | Fraction of 252-session window below current iv30 | — | — | 252-session window | model-derived |
| OI Daily Delta | oi_daily_delta | derived | `total_oi(today) - LAG(total_oi)` | all | all | as-of pull_date | model-derived |
| Dealer Net Gamma | dealer_net_gamma | derived | `SUM(gex_contribution)` across all contracts | all | all | as-of pull_date | model-derived |
| Top OI Strikes | top_oi_strike_1/2/3 | derived | `ROW_NUMBER() ORDER BY SUM(OI) DESC` | all | all | as-of pull_date | model-derived |
| Social Mentions | social_mention_count | unsupported | Seed fixture only | — | — | static | fixture only |
| Social Sentiment | social_sentiment_score | unsupported | Seed fixture only | — | — | static | fixture only |

### 2.8 Dashboard Fact-Check Links

URLs and status labels reflect browser-verified checks run 2026-05-23. These links are **comparator references** for manual verification — the mart does not ingest values from these sites. Status values: **comparator** = external site shows a comparable metric for GME (our value is model-derived, not sourced from this link); **proxy** = asset confirmed, metric definition may differ; **unsupported** = no viable free live source; **unverified** = page blocked (bot protection or HTTP error).

| Dashboard Card | Metric | Reference Source | Verified URL | Link Status |
|----------------|--------|-----------------|--------------|-------------|
| Spot Price | spot | Yahoo Finance | <https://finance.yahoo.com/quote/GME/> | comparator |
| Max Pain | max_pain_strike | ChartExchange (standard class) | <https://chartexchange.com/symbol/nyse-gme/optionchain/summary/?adjustment=GME> | comparator |
| P/C Ratio | pc_ratio | ChartExchange (standard class) | <https://chartexchange.com/symbol/nyse-gme/optionchain/summary/?adjustment=GME> | comparator |
| Net GEX | net_gex | Barchart Gamma Exposure | <https://www.barchart.com/stocks/quotes/GME/gamma-exposure> | comparator |
| IV30 | iv30 | Barchart Volatility & Greeks | <https://www.barchart.com/stocks/quotes/GME/volatility-greeks> | comparator |
| Gamma Flip | gamma_flip_point | Barchart Gamma Exposure | <https://www.barchart.com/stocks/quotes/GME/gamma-exposure> | comparator |
| HV20 | hv20 | Barchart Volatility & Greeks | <https://www.barchart.com/stocks/quotes/GME/volatility-greeks> | comparator |
| IV Rank | iv_rank | Barchart Volatility & Greeks | <https://www.barchart.com/stocks/quotes/GME/volatility-greeks> | comparator |
| IV Percentile | iv_percentile | Barchart Volatility & Greeks | <https://www.barchart.com/stocks/quotes/GME/volatility-greeks> | comparator |
| OI Daily Delta | oi_daily_delta | Barchart Options Prices | <https://www.barchart.com/stocks/quotes/GME/options> | comparator |
| Dealer Net Gamma | dealer_net_gamma | Barchart Gamma Exposure | <https://www.barchart.com/stocks/quotes/GME/gamma-exposure> | comparator |
| Top OI Strikes | top_oi_strike_1/2/3 | Barchart Options Prices | <https://www.barchart.com/stocks/quotes/GME/options> | comparator |
| Social Mentions | social_mention_count | — | — | unsupported |
| Social Sentiment | social_sentiment_score | — | — | unsupported |

**ChartExchange notes:**
- ChartExchange visibly supports adjustment-specific routes: `?adjustment=GME` for standard contracts, `?adjustment=GME1` for adjusted delivery class.
- Browser-verified 2026-05-23: standard GME Jun 18, 2026 Max Pain `$22.00`, P/C `0.29`; adjusted GME1 Max Pain `$15.00`, P/C `0.18`.
- The unqualified summary URL displays adjusted-class values — always use `?adjustment=GME` for standard comparator.
- ChartExchange is a browser-verified comparator link only. API/data-use suitability for warehouse ingestion is not confirmed; do not pull values into MotherDuck until terms are reviewed.

**Rejected / broken links (removed from dashboard fact-check references):**
- **SqueezeMetrics DIX Monitor** (`squeezemetrics.com/monitor`): tracks S&P 500 market-wide GEX, not individual stock GEX.
- **Yahoo Finance Community**: a discussion forum, not a structured data endpoint.
- **SwaggyStocks Max Pain** (`swaggerstocks.com`): navigation failed.
- **ApeWisdom** (`apewisdom.io/stocks/GME/`): aggregation scope differs; social metrics reclassified as unsupported.
- **Maximum-Pain.com** (`maximum-pain.com/options/GME`): replaced by ChartExchange which shows adjustment-specific routes matching contract-class-scoped calculation.
- **Market Chameleon IV** (`marketchameleon.com/Overview/GME/IV/`): `ERR_HTTP2_PROTOCOL_ERROR` in Playwright 2026-05-23; cannot be represented as browser-verified.
- **Barchart options-overview** (`barchart.com/stocks/quotes/GME/options-overview`): CloudFront `403 ERROR` in Playwright 2026-05-23; cannot be represented as browser-verified. Note: other Barchart sub-pages (gamma-exposure, volatility-greeks, put-call-ratios, options) remain accessible.

**Comparator label notes:**
- All model-derived metrics use **comparator** status for their reference links. The mart computes these values from CBOE inputs using documented formulas; the external links are for manual cross-verification only and may use different calculation methods, lookback windows, or data sources.
- `social_mention_count` and `social_sentiment_score` are **unsupported**: no free live source matches this mart's definition. Values use seed fixtures for CI only.

### 2.9 DQC Outputs

| Control Class | What It Validates |
|---------------|-------------------|
| PK Integrity | Primary keys (date_key, pull_date) are not null and unique |
| FK Integrity | ADS pull_date resolves to gme_dim_date.full_date |
| Freshness | ODS pull_ts_utc is not null (data was actually pulled) |
| Completeness | Minimum row counts per layer (ODS, DWD, DWS) |
| Accepted Ranges | Strikes > 0, OI ≥ 0, spot > 0, P/C ratio ∈ [0, 50] |
| Duplicate Detection | No duplicate (pull_date, option_symbol) in DWD |
| Null-Rate | Greeks null rate < 5% in DWD |
| Business Reconciliation | GEX vs external source (waived — no free gamma provider) |

### 2.10 ER Calendar and Instrument Metadata Metrics

These metrics extend the mart with publicly derivable analytics from the earnings calendar and options chain instrument metadata. They do not expose operator-specific data.

#### ER Cycle Phase

| Metric | Definition | Formula | Layer |
|--------|-----------|---------|-------|
| days_to_next_er | Calendar days until the next expected GME earnings release | `next_er_date - pull_date` | DWS |
| er_cycle_phase | Four-phase ER cycle classification derived from `days_to_next_er` | Phase 1 (Low-IV): DTE ∈ [14, 60]; Phase 2 (Pre-ER lift): DTE ∈ [3, 13]; Phase 3 (Earnings event): DTE ∈ [0, 2]; Phase 4 (Post-ER): DTE < 0 | DWS |

- `next_er_date` is loaded from a seed table (`gme_dim_er_calendar`) populated from public earnings release announcements.
- Phase boundaries are approximate and aligned to typical options market behavior around earnings events.
- This is a public educational metric. It does not encode operator position decisions or private trading rules.

#### Warrant Series Classification

| Metric | Definition | Formula | Layer |
|--------|-----------|---------|-------|
| warrant_series | Classification of a GME options chain contract into its instrument series | Derived from option symbol prefix: `GME` = standard option; `GMEWARB` or `GME.WS` = warrant series (Series A, strike ~$19.94, expiry Jun 2026, per public SEC filing); `GME1` = dividend warrant series (strike $32.00, expiry Oct 30 2026, per public SEC filing) | DWD |

- This field enables filtering the options chain by instrument type.
- The warrant series terms are publicly available in GameStop SEC filings (Form 8-A, Form S-1).
- This field contains only public instrument metadata; no operator position data is included.

#### Intraday Session Phase

| Metric | Definition | Formula | Layer |
|--------|-----------|---------|-------|
| session_phase | Intraday market session block classification | `pre_market` (04:00–09:29 ET); `morning` (09:30–10:59); `midday` (11:00–13:59); `afternoon` (14:00–15:59); `after_hours` (16:00–20:00) based on `pull_ts_utc` | ODS / DWD |

- This field supports session-level slicing of intraday option chain snapshots.
- Derived purely from the pull timestamp; contains no position data.

---

## 3. Domain Glossary

| Term | Definition |
|------|-----------|
| **Option contract** | A financial derivative giving the holder the right (not obligation) to buy (call) or sell (put) an underlying asset at a specified strike price before expiration. |
| **Strike price** | The price at which the option holder can buy or sell the underlying asset. |
| **Expiry (expiration)** | The date on which the option contract ceases to exist. |
| **Days to expiry (DTE)** | Calendar days remaining until the option expires: `expiry - pull_date`. |
| **Open interest (OI)** | The total number of outstanding option contracts that have not been settled or closed. |
| **Implied volatility (IV)** | The market's forecast of the underlying asset's price volatility, extracted from the option's market price using a pricing model. |
| **Historical volatility (HV)** | The observed annualized standard deviation of the underlying's logarithmic daily returns over a lookback window. |
| **Greeks** | Partial derivatives of the option price with respect to various factors: delta (underlying price), gamma (delta's rate of change), theta (time decay), vega (volatility), rho (interest rate). |
| **Gamma exposure (GEX)** | A dollar-denominated measure of how much delta-hedging activity a market maker must perform for a 1% move in the underlying. Positive GEX implies dealers dampen moves; negative GEX implies dealers amplify moves. |
| **Gamma flip point** | The underlying price at which cumulative net GEX crosses zero — above this price, dealers are long gamma (stabilizing); below, short gamma (destabilizing). |
| **Max pain** | The strike price at which the aggregate dollar value of in-the-money options is minimized — the price where option holders collectively lose the most at expiration. |
| **Put/call ratio (P/C ratio)** | The ratio of total put open interest to total call open interest. Values > 1 suggest bearish positioning; < 1 suggest bullish positioning. |
| **IV rank** | Measures where the current IV30 sits relative to its 252-session range: `(current - min) / (max - min)`. A rank of 0.8 means IV is in the top 20% of its historical range. |
| **IV percentile** | The fraction of 252 sessions where IV30 was lower than the current level. A percentile of 0.9 means IV was lower 90% of the time. |
| **OCC symbol** | The standardized Options Clearing Corporation symbol format: `{TICKER}{YYMMDD}{C/P}{strike*1000}` (e.g., `GME260620C00025000` = GME $25 call expiring June 20, 2026). |
| **Series type** | Classification of option contracts by DTE: WEEKLY (≤ 7 DTE), MONTHLY (8–365 DTE), LEAP (> 365 DTE). |
| **Dealer net gamma** | Sum of all per-contract GEX contributions across the entire options chain for a given day. |
| **OI daily delta** | The change in total open interest from the previous trading day. Positive values indicate new positions being opened; negative values indicate positions being closed. |
| **Social sentiment score** | Mention-weighted average sentiment from social media sources, ranging from −1 (extremely bearish) to +1 (extremely bullish). |
| **Conformed dimension** | A Kimball dimension shared across multiple fact tables or marts, ensuring consistent filtering and grouping. |
| **Degenerate dimension** | A dimension attribute (e.g., option_symbol, ticker) stored directly in the fact table rather than in a separate dimension table. |
| **ODS (Operational Data Store)** | The first landing layer for raw ingested data, minimally transformed. |
| **DWD (Data Warehouse Detail)** | The cleaned, filtered, and enriched fact layer with business rules applied. |
| **DWS (Data Warehouse Summary)** | Pre-aggregated summary tables optimized for specific analytical patterns. |
| **ADS (Analytical Data Store)** | The final consumption layer — a denormalized one-big-table (OBT) designed for dashboards and BI tools. |
| **DQC (Data Quality Contract)** | A structured catalog of data quality controls with defined thresholds, severities, and test implementations. |

---

## 4. Data Sources

| Source | Type | Auth Required | Format | Freshness | Data Contents |
|--------|------|---------------|--------|-----------|---------------|
| CBOE Delayed Quotes API | Live HTTP (httpfs) | No | JSON | 15-minute delay from live market | Full options chain: ~1,300 contracts per pull, including all Greeks, OI, volume, bid/ask, underlying close |
| Bundled Parquet Fixture | Static file | No | Parquet | Snapshot (offline CI) | Same schema as CBOE live, bundled for reproducible CI runs |
| Yahoo Finance Chart API | Seed CSV | No | CSV | Daily closes | GME underlying close prices (260 trading days, 2025-05-08 to 2026-05-20) |
| Reddit / Social Sources | Seed CSV | No | CSV | Daily | Social mention counts and sentiment scores, fixture for CI |
| Conformed Date Dimension | Seed CSV | No | CSV | Static (2024–2027) | Calendar dates with trading day flags, weekday names, quarter, holiday indicators |

### CBOE Data Contract

- **Endpoint:** `https://cdn.cboe.com/api/global/delayed_quotes/options/GME.json`
- **Rate limits:** None (public CDN)
- **Response size:** ~5–10 MB JSON payload
- **Fields used:** `options[]` array with `option` (OCC symbol), `bid`, `ask`, `iv`, `open_interest`, `volume`, `delta`, `gamma`, `theta`, `vega`, `rho`, `theo`, `change`, `open`, `high`, `low`, `tick`, `last_trade_price`, `last_trade_time`, `percent_change`, `prev_day_close`; top-level `close` (underlying), `timestamp`
- **Fixture toggle:** `use_fixture: true` (default) uses bundled Parquet; `false` pulls live

### Reconciliation Sources

The mart includes an OpenBB provider probe (`scripts/openbb_gex_probe.py`) that evaluates four providers for independent GEX verification:

| Provider | Status | Reason |
|----------|--------|--------|
| CBOE (via OpenBB) | not_independent | Same upstream endpoint as primary ODS |
| yfinance | insufficient_fields | Returns chains without gamma — GEX not computable |
| intrinio | credentials_required | Paid API key needed |
| tradier | credentials_required | Paid API key + openbb-tradier plugin needed |

**Reconciliation outcome:** No free, independent gamma source exists. Proxy reconciliation (ODS-to-DWD row count) is in place; GEX reconciliation carries a waiver.

---

## 5. Stakeholder Needs and Personas

### 5.1 Framework Evaluator (Primary)

| Attribute | Detail |
|-----------|--------|
| Role | Data engineer evaluating mart-forge for adoption |
| Goal | Validate that the framework produces a complete, working Kimball warehouse from real data |
| Needs | End-to-end `dbt seed && dbt run && dbt test` in under 2 minutes, clear DQC scorecard, reproducible results from fixture |
| Success criteria | All tests pass, dashboard renders, metrics match public verification sources |

### 5.2 Options Researcher

| Attribute | Detail |
|-----------|--------|
| Role | Financial analyst studying options market structure |
| Goal | Understand Kimball patterns for modeling options data (GEX, max pain, IV surfaces) |
| Needs | Clear metric definitions with actual SQL, traceability from business question to dashboard output |
| Success criteria | Can adapt the mart to a different ticker or asset class |

### 5.3 Agent Builder

| Attribute | Detail |
|-----------|--------|
| Role | AI developer building automated data warehouse agents |
| Goal | Use the mart as a reference for structuring agent-built warehouses with quality gates |
| Needs | Methodology-first approach (BRD → TDD → scaffold → DQC), machine-readable artifacts (mart.yml, dqc_scorecard.json) |
| Success criteria | Can replicate the pattern for a new domain using the framework's Phase A–E lifecycle |

---

## 6. Refresh Cadence

| Parameter | Value |
|-----------|-------|
| Schedule | `45 20 * * 1-5` (8:45 PM ET, weekdays) |
| Timezone | America/New_York |
| Holiday handling | Skip (US market holidays; uses `is_trading_day` in dim_date) |
| Pipeline steps | seed → run → test |
| Fail-fast | Yes (pipeline halts on first error) |
| Timeout | 10 minutes |
| Incremental strategy | Merge on `(pull_date, option_symbol)` for ODS and DWD |

---

## 7. Data Sensitivity Statement

All data in this mart is **publicly available**:

- **Options chain data:** CBOE delayed quotes are freely accessible via a public CDN endpoint with no authentication. Data is delayed 15 minutes from live market prices — it does not constitute real-time market data.
- **Greeks:** Delta, gamma, theta, vega, rho, and IV are computed by CBOE from publicly available option prices.
- **Underlying closes:** Sourced from Yahoo Finance's public chart API.
- **Social sentiment:** Aggregated from public Reddit/social media posts. No personally identifiable information (PII) is collected or stored.

No confidential, proprietary, or personally identifiable data is ingested, stored, or exposed by this mart. The mart is safe for open-source distribution.

---

## 8. Sign-Off

| Role | Name | Responsibility | Date | Status |
|------|------|---------------|------|--------|
| Operator (data owner) | (open-source example) | Framework maintainer | 2026-05-23 | approved |
| Consumer (primary user) | (community) | Framework evaluators and contributors | 2026-05-23 | approved |

**Solo-operator exception:** This is an open-source example mart. The framework maintainer serves as both operator and consumer for validation purposes. The BRD is approved for use as the canonical GME options mart specification.

---

## Appendix A: Section 2.8 Link Verification Evidence

Link verification was performed on 2026-05-23 using Playwright/Chromium 1.60.0 in headless mode. Each URL was loaded and the page title and body text were searched for the target asset (GME/GameStop) and the claimed metric. The full machine-readable report is committed at `examples/gme-options-mart/brd_link_verification.json`.

All dashboard metrics are model-derived from CBOE inputs; external links are **comparator references** for manual cross-verification, not data sources.

### Browser-Verified Comparators

| URL | Dashboard Card(s) | Status | Finding |
|-----|-------------------|--------|---------|
| <https://finance.yahoo.com/quote/GME/> | Spot Price | comparator | GME stock price confirmed. Mart spot is source_native from CBOE `underlying_close`. |
| <https://chartexchange.com/symbol/nyse-gme/optionchain/summary/?adjustment=GME> | Max Pain, P/C Ratio | comparator | Standard GME Jun 18, 2026 Max Pain $22.00, P/C 0.29 confirmed. `?adjustment=GME` scopes to standard contract class. ChartExchange is comparator only; API/data-use suitability for ingestion not confirmed. |
| <https://www.barchart.com/stocks/quotes/GME/gamma-exposure> | Net GEX, Gamma Flip, Dealer Net Gamma | comparator | GME GEX confirmed. Barchart GEX formula may differ from mart formula. |
| <https://www.barchart.com/stocks/quotes/GME/volatility-greeks> | IV30, HV20, IV Rank, IV Percentile | comparator | GME IV/HV confirmed. Barchart lookback window and weighting may differ. |
| <https://www.barchart.com/stocks/quotes/GME/options> | OI Daily Delta, Top OI Strikes | comparator | GME options chain with per-contract OI confirmed. |

### Unsupported

| Metric | Reason |
|--------|--------|
| `social_mention_count` | No free live source matches this mart's aggregation definition. Seed fixture for CI only. |
| `social_sentiment_score` | No free live source provides a mention-weighted average sentiment score in the −1 to +1 range. Seed fixture for CI only. |

### Unverified (bot protection / inaccessible)

| URL | Expected Source | Note |
|-----|----------------|------|
| <https://investor.gamestop.com/events-presentations> | GameStop official ER calendar | Cloudflare/bot protection in headless browser; known public source for earnings dates |

### Rejected Links

| Prior Reference | URL | Reason Rejected |
|-----------------|-----|----------------|
| SqueezeMetrics DIX Monitor | <https://squeezemetrics.com/monitor> | **Wrong asset**: tracks S&P 500 market-wide GEX only, not individual stock GEX. |
| Yahoo Finance Community | <https://finance.yahoo.com/quote/GME/community> | Discussion forum, not a structured data endpoint. |
| SwaggyStocks Max Pain | <https://swaggerstocks.com/options.php?ticker=GME> | Navigation failed (execution context destroyed on redirect). |
| QuiverQuant WallStreetBets | <https://www.quiverquant.com/wallstreetbets/?ticker=GME> | **Wrong asset**: page shows SPY/S&P 500 content by default, not GME. |
| ApeWisdom | <https://apewisdom.io/stocks/GME/> | Aggregation scope differs from mart fixture definition. Social metrics reclassified as unsupported. |
| Maximum-Pain.com | <https://maximum-pain.com/options/GME> | Replaced by ChartExchange which supports adjustment-specific routes (`?adjustment=GME` for standard class). Maximum-Pain.com does not distinguish standard vs adjusted contract class. |
| Market Chameleon IV | <https://marketchameleon.com/Overview/GME/IV/> | `ERR_HTTP2_PROTOCOL_ERROR` in Playwright 2026-05-23. Cannot be represented as browser-verified. |
| Barchart options-overview | <https://www.barchart.com/stocks/quotes/GME/options-overview> | CloudFront `403 ERROR` in Playwright 2026-05-23. Other Barchart sub-pages remain accessible. |
| Barchart Put/Call Ratios | <https://www.barchart.com/stocks/quotes/GME/put-call-ratios> | Replaced by ChartExchange which shows per-expiry, per-contract-class P/C matching mart scoping. |
