# Business Requirements Document: GME Options Mart

> Version 1.0 — Open-source example for the mart-forge framework.

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

### 2.7 Dashboard Outputs

URLs and status labels reflect browser-verified checks run 2026-05-23. Status values: **exact** = asset and metric confirmed; **proxy** = asset confirmed, metric definition may differ; **unsupported** = no viable free live source; **unverified** = page blocked (bot protection or HTTP error).

| Dashboard Card | Metric | Reference Source | Verified URL | Status |
|----------------|--------|-----------------|--------------|--------|
| Spot Price | spot | Yahoo Finance | <https://finance.yahoo.com/quote/GME/> | exact |
| Max Pain | max_pain_strike | Maximum-Pain.com | <https://maximum-pain.com/options/GME> | exact |
| Max Pain Convergence | max_pain_convergence_pct | Maximum-Pain.com | <https://maximum-pain.com/options/GME> | proxy |
| P/C Ratio | pc_ratio | Barchart Put/Call Ratio | <https://www.barchart.com/stocks/quotes/GME/put-call-ratios> | exact |
| Net GEX | net_gex | Barchart Gamma Exposure | <https://www.barchart.com/stocks/quotes/GME/gamma-exposure> | exact |
| IV30 | iv30 | Barchart Volatility & Greeks | <https://www.barchart.com/stocks/quotes/GME/volatility-greeks> | exact |
| Gamma Flip | gamma_flip_point | Barchart Gamma Exposure | <https://www.barchart.com/stocks/quotes/GME/gamma-exposure> | proxy |
| HV20 | hv20 | Barchart Volatility & Greeks | <https://www.barchart.com/stocks/quotes/GME/volatility-greeks> | exact |
| IV Rank | iv_rank | Barchart Volatility & Greeks | <https://www.barchart.com/stocks/quotes/GME/volatility-greeks> | exact |
| IV Percentile | iv_percentile | Barchart Volatility & Greeks | <https://www.barchart.com/stocks/quotes/GME/volatility-greeks> | proxy |
| OI Daily Delta | oi_daily_delta | Barchart Options Prices | <https://www.barchart.com/stocks/quotes/GME/options> | proxy |
| Dealer Net Gamma | dealer_net_gamma | Barchart Gamma Exposure | <https://www.barchart.com/stocks/quotes/GME/gamma-exposure> | proxy |
| Social Mentions | social_mention_count | ApeWisdom (Reddit tracker) | <https://apewisdom.io/stocks/GME/> | proxy |
| Social Sentiment | social_sentiment_score | — | — | unsupported |
| Top OI Strikes | top_oi_strike_1/2/3 | Barchart Options Prices | <https://www.barchart.com/stocks/quotes/GME/options> | exact |
| ER Cycle Phase | er_cycle_phase | GameStop Investor Relations | <https://investor.gamestop.com/events-presentations> | unverified |
| Days to Next ER | days_to_next_er | GameStop Investor Relations | <https://investor.gamestop.com/events-presentations> | unverified |
| Warrant Series | warrant_series | Barchart Options Chain | <https://www.barchart.com/stocks/quotes/GME/options> | proxy |

**Rejected links:**
- **SqueezeMetrics DIX Monitor** (`squeezemetrics.com/monitor`): tracks S&P 500 market-wide GEX, not individual stock GEX. All three prior SqueezeMetrics references (net_gex, gamma_flip_point, dealer_net_gamma) replaced with Barchart Gamma Exposure.
- **Yahoo Finance Community**: a discussion forum, not a structured data endpoint. Removed as validator for both social metrics.
- **SwaggyStocks Max Pain** (`swaggerstocks.com`): navigation to the options page failed (execution context error on redirect). Replaced with Maximum-Pain.com which verified successfully.

**Status label notes:**
- `gamma_flip_point` and `dealer_net_gamma` are marked **proxy** because Barchart shows GEX by strike (from which the zero-crossing and net total are derivable) but may not display these derived scalars as single labeled values.
- `iv_percentile` is **proxy** because Barchart's lookback window may differ from this mart's 252-session definition.
- `social_sentiment_score` is **unsupported**: no free live source provides a mention-weighted average sentiment score matching this mart's −1 to +1 definition. The mart's value uses a seed fixture and is not valid for live operator comparison.
- `er_cycle_phase` and `days_to_next_er` are **unverified** because the GameStop Investor Relations page was inaccessible to headless browser verification; the source is the official public ER calendar.

### 2.8 DQC Outputs

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

### 2.9 ER Calendar and Instrument Metadata Metrics

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

## Appendix A: Section 2.7 Link Verification Evidence

Link verification was performed on 2026-05-23 using Playwright/Chromium 1.60.0 in headless mode. Each URL was loaded and the page title and body text were searched for the target asset (GME/GameStop) and the claimed metric. The full machine-readable report is committed at `examples/gme-options-mart/brd_link_verification.json`.

### Verified (exact)

| URL | Confirms |
|-----|----------|
| <https://finance.yahoo.com/quote/GME/> | GME stock quote — "GameStop Corp. (GME) Stock Price, News, Quote & History" |
| <https://maximum-pain.com/options/GME> | GME Max Pain Calculator with per-expiry strikes and OI |
| <https://www.barchart.com/stocks/quotes/GME/put-call-ratios> | "GME Put/Call Ratio for Gamestop Corp Stock — Barchart.com" |
| <https://www.barchart.com/stocks/quotes/GME/gamma-exposure> | "GME Gamma Exposure (GEX) for Gamestop Corp Stock — Barchart.com" |
| <https://www.barchart.com/stocks/quotes/GME/volatility-greeks> | "GME Options Volatility & Greeks for Gamestop Corp Stock — Barchart.com" |
| <https://www.barchart.com/stocks/quotes/GME/options> | "GME Options Prices for Gamestop Corp Stock — Barchart.com" |

### Verified (proxy)

| URL | Asset | Proxy Limitation |
|-----|-------|-----------------|
| <https://apewisdom.io/stocks/GME/> | GME Reddit mentions and sentiment history | Aggregation scope differs from mart fixture |
| <https://www.barchart.com/stocks/quotes/GME/gamma-exposure> | GEX by strike (gamma flip and dealer net gamma derivable) | Derived scalars may not be labeled as single values |
| <https://www.barchart.com/stocks/quotes/GME/volatility-greeks> | IV percentile visible | Lookback window may differ from 252-session mart definition |

### Unsupported

| Metric | Reason |
|--------|--------|
| `social_sentiment_score` | No free live source provides a mention-weighted average sentiment score in the −1 to +1 range. Mart value uses a seed fixture and is not suitable for live comparison. |

### Unverified (bot protection / inaccessible)

| URL | Expected Source | Note |
|-----|----------------|------|
| <https://investor.gamestop.com/events-presentations> | GameStop official ER calendar | Cloudflare/bot protection in headless browser; known public source |
| <https://marketchameleon.com/Overview/GME/IV/> | IV rank, IV percentile | Cloudflare protection blocks headless; valid public source for manual verification |

### Rejected Links

| Prior Reference | URL | Reason Rejected |
|-----------------|-----|----------------|
| SqueezeMetrics DIX Monitor | <https://squeezemetrics.com/monitor> | **Wrong asset**: tracks S&P 500 market-wide GEX only, not individual stock GEX. GME not found on page. |
| Yahoo Finance Community | <https://finance.yahoo.com/quote/GME/community> | Not a structured data source; discussion forum only. Removed from both social metrics. |
| SwaggyStocks Max Pain | <https://swaggerstocks.com/options.php?ticker=GME> | Navigation failed (execution context error on redirect); replaced by Maximum-Pain.com. |
