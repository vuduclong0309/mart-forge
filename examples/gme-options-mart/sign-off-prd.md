# Sign-Off PRD: gme-options-mart

> Generated from `mart.yml`. This is the open-source example mart for the mart-forge framework.
>
> V1.1 (2026-05-23): Right-anchored OCC parsing, contract_class classification, per-expiry/per-class max pain via `gme_dws_max_pain_by_expiry_1d`, standard-class P/C ratio scoping, updated traceability matrices.

---

## 1. Business Purpose

**Mart name:** gme-options-mart
**Version:** 1.0

### Why this mart exists

Demonstrates the mart-forge framework building a complete Kimball data warehouse from a live, freely available data source (CBOE delayed options quotes). Serves as the canonical example that the framework's methodology, templates, and skills work end-to-end against real market data.

### Stakeholder problem

Data engineers evaluating mart-forge need a working example that goes beyond synthetic CSV seeds. This mart proves the framework handles live API ingestion, complex derived metrics (GEX, max pain), and a full DQC control catalog against real-world data.

### Consumer personas

| Persona | Role | How they use this mart |
|---------|------|------------------------|
| Framework evaluator | Data engineer | Runs the example to validate mart-forge works before adopting it |
| Options researcher | Analyst | Studies the Kimball patterns for financial options data modeling |
| Agent builder | AI developer | Uses as a reference for structuring agent-built warehouses |

---

## 2. Source Systems

| Provider | Auth required | Rate limits | Freshness SLA |
|----------|---------------|-------------|---------------|
| CBOE (cdn.cboe.com) | No | None (public delayed quotes) | 15-minute delay from live market |

**Notes:**
- CBOE delayed quotes are freely available via httpfs (no API key).
- Returns ~1300 option contracts per pull for GME.
- Data includes all Greeks (delta, gamma, theta, vega, rho, IV) computed by CBOE.

---

## 3. Grain & Dimensions

### Fact grain

**Primary grain:** per-contract-per-day (one row per option contract per pull date)

### Bus matrix

| Dimension | Conformed | SCD type | Notes |
|-----------|-----------|----------|-------|
| gme_dim_date | yes | Type 0 | Immutable calendar with trading day flag |

### Conformed dimensions

- `gme_dim_date` — reusable across any mart needing a date calendar

### Local dimensions

- None (option contract attributes are carried as degenerate dimensions in the fact table)

---

## 4. Refresh Cadence

| Parameter | Value |
|-----------|-------|
| Cron expression | `45 20 * * 1-5` |
| Timezone | America/New_York |
| Holiday handling | Skip (US market holidays) |
| Pipeline steps | seed, run, test |
| Fail-fast | true |
| Timeout (minutes) | 10 |

**Holiday policy:** Uses `is_trading_day` flag in dim_date. Pipeline skips on non-trading days (weekends + US market holidays).

---

## 5. DQC Controls

| # | Control class | Metric / test description | Tolerance | Severity |
|---|---------------|--------------------------|-----------|----------|
| 1 | PK Integrity | `not_null` + `unique` on date_key, pull_date PKs | 0 | error |
| 2 | FK Integrity | ADS pull_date resolves to dim_date | 0 | error |
| 3 | Freshness | `pull_ts_utc` is not null on all ODS rows | 0 | error |
| 4 | Completeness | Minimum row counts: ODS>=100, DWD>=50, DWS>=10 | 0 | error |
| 5 | Accepted Ranges | Strikes positive, OI non-negative, spot positive, P/C ratio 0-50 | 0 | error |
| 6 | Duplicate Detection | No duplicate (pull_date, option_symbol) in DWD | 0 | error |
| 7 | Null-Rate | Greeks null rate < 5% in DWD | 5% | warn |
| 8 | Business Reconciliation | GEX total vs external — **unavailable** (paywalled source, waiver granted) | 0.5 | warn |

**Scorecard artifact:** `dqc_scorecard.json`
**Control catalog enforcement:** required

---

## 6. Column-Level Calculation Specifications

Every derived metric in this mart is specified here with its exact SQL expression, source model, and traceability to the implementing dbt model.

### 6.1 GEX Contribution (per-contract)

**Definition:** Gamma Exposure contribution measures the dollar-denominated gamma exposure of a single option contract, indicating how much delta-hedging activity that contract may generate.

**Formula:**

```
GEX_contribution = gamma * open_interest * 100 * spot^2 * 0.01 * sign
```

Where:
- `gamma` — CBOE-computed option gamma (from ODS)
- `open_interest` — number of outstanding contracts (from ODS)
- `100` — contract multiplier (100 shares per option contract)
- `spot^2` — underlying close price squared
- `0.01` — scaling factor (converts to standard GEX units)
- `sign` — +1 for calls, -1 for puts (calls add positive gamma, puts subtract)

**SQL expression** (`gme_dwd_option_contract_di.sql`, lines 32-38):

```sql
COALESCE(ods.gamma, 0)
    * COALESCE(ods.open_interest, 0)
    * 100
    * POWER(ods.underlying_close, 2)
    * 0.01
    * CASE WHEN ods.option_type = 'call' THEN 1 ELSE -1 END
                                                   AS gex_contribution
```

**Null handling:** `COALESCE(..., 0)` on gamma and open_interest ensures contracts with missing Greeks contribute zero rather than propagating NULLs.

**Traceability:**
| Source field | Source model | Target column | Target model |
|-------------|-------------|---------------|--------------|
| gamma | gme_ods_cboe_options_chain | gex_contribution | gme_dwd_option_contract_di |
| open_interest | gme_ods_cboe_options_chain | gex_contribution | gme_dwd_option_contract_di |
| underlying_close | gme_ods_cboe_options_chain | gex_contribution | gme_dwd_option_contract_di |
| option_type | gme_ods_cboe_options_chain | gex_contribution | gme_dwd_option_contract_di |

### 6.2 Net GEX by Strike (daily aggregation)

**Definition:** Aggregates per-contract GEX contributions to the strike level, split by call/put, producing a net GEX per strike per day.

**SQL expression** (`gme_dws_strike_gex_1d.sql`, lines 8-11):

```sql
SUM(CASE WHEN option_type = 'call' THEN gex_contribution ELSE 0 END) AS call_gex,
SUM(CASE WHEN option_type = 'put'  THEN gex_contribution ELSE 0 END) AS put_gex,
SUM(gex_contribution)                                                 AS net_gex
```

**GEX rank** (lines 16-19): strikes ranked by absolute net GEX magnitude within each day:

```sql
ROW_NUMBER() OVER (
    PARTITION BY pull_date, ticker
    ORDER BY ABS(SUM(gex_contribution)) DESC
)                                                                     AS gex_rank
```

**Aggregation grain:** `GROUP BY pull_date, ticker, strike, expiry, dte, series_type`

**Traceability:**
| Source column | Source model | Target column | Target model |
|--------------|-------------|---------------|--------------|
| gex_contribution | gme_dwd_option_contract_di | call_gex, put_gex, net_gex | gme_dws_strike_gex_1d |
| option_type | gme_dwd_option_contract_di | call_gex, put_gex | gme_dws_strike_gex_1d |

### 6.3 Total Net GEX (market-wide daily)

**Definition:** Sum of net GEX across all strikes for a given day. The top GEX strike is the strike with the highest absolute net GEX.

**SQL expression** (`gme_dws_daily_snapshot_1d.sql`, lines 1-11):

```sql
WITH gex_agg AS (
    SELECT
        pull_date, ticker,
        SUM(net_gex)                                               AS net_gex,
        (SELECT strike FROM gme_dws_strike_gex_1d g2
         WHERE g2.pull_date = g1.pull_date AND g2.ticker = g1.ticker
         ORDER BY ABS(g2.net_gex) DESC LIMIT 1)                   AS top_gex_strike
    FROM gme_dws_strike_gex_1d g1
    GROUP BY pull_date, ticker
)
```

**Traceability:**
| Source column | Source model | Target column | Target model |
|--------------|-------------|---------------|--------------|
| net_gex | gme_dws_strike_gex_1d | net_gex | gme_dws_daily_snapshot_1d |
| strike, net_gex | gme_dws_strike_gex_1d | top_gex_strike | gme_dws_daily_snapshot_1d |

### 6.4 Max Pain Strike

**Definition:** The strike price at which the total dollar value of in-the-money options is minimized — the price where option holders would collectively lose the most money at expiration.

**Scope:** Per-expiry, per-contract-class. The dashboard shows the nearest standard-class expiry.

**Algorithm:**
1. Select DISTINCT strike candidates within each (pull_date, ticker, expiry, contract_class) partition
2. Cross-join candidates against contracts in the same partition
3. For each candidate strike, calculate total pain:
   - **Calls ITM below candidate:** `(candidate - call_strike) * call_OI * 100`
   - **Puts ITM above candidate:** `(put_strike - candidate) * put_OI * 100`
4. Select the candidate with the minimum total pain per (pull_date, ticker, expiry, contract_class)

**SQL expression** (`gme_dws_max_pain_by_expiry_1d.sql`):

```sql
WITH contracts AS (
    SELECT pull_date, ticker, expiry, strike, option_type, open_interest, contract_class
    FROM gme_dwd_option_contract_di
),
candidates AS (
    SELECT DISTINCT pull_date, ticker, expiry, contract_class, strike AS candidate
    FROM contracts
),
pain_calc AS (
    SELECT c.pull_date, c.ticker, c.expiry, c.contract_class, c.candidate,
        SUM(CASE
            WHEN ct.option_type = 'call' AND ct.strike < c.candidate
            THEN (c.candidate - ct.strike) * ct.open_interest * 100
            WHEN ct.option_type = 'put' AND ct.strike > c.candidate
            THEN (ct.strike - c.candidate) * ct.open_interest * 100
            ELSE 0
        END) AS total_pain
    FROM candidates c
    INNER JOIN contracts ct ON c.pull_date = ct.pull_date AND c.ticker = ct.ticker
        AND c.expiry = ct.expiry AND c.contract_class = ct.contract_class
    GROUP BY c.pull_date, c.ticker, c.expiry, c.contract_class, c.candidate
)
SELECT pull_date, ticker, expiry, contract_class,
    candidate AS max_pain_strike, total_pain AS min_total_pain
FROM pain_calc
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY pull_date, ticker, expiry, contract_class ORDER BY total_pain ASC
) = 1
```

**Snapshot join** (`gme_dws_daily_snapshot_1d.sql`): The daily snapshot selects the nearest standard-class expiry:

```sql
max_pain AS (
    SELECT pull_date, ticker, max_pain_strike, expiry AS max_pain_expiry
    FROM gme_dws_max_pain_by_expiry_1d
    WHERE contract_class = 'standard'
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY pull_date, ticker ORDER BY expiry ASC
    ) = 1
)
```

**Max pain convergence:**

```sql
ROUND(ABS(s.spot - mp.max_pain_strike) / s.spot * 100, 2) AS max_pain_convergence_pct
```

**Traceability:**
| Source column | Source model | Target column | Target model |
|--------------|-------------|---------------|--------------|
| strike, option_type, open_interest, contract_class | gme_dwd_option_contract_di | max_pain_strike, min_total_pain | gme_dws_max_pain_by_expiry_1d |
| max_pain_strike, expiry | gme_dws_max_pain_by_expiry_1d | max_pain_strike, max_pain_expiry | gme_dws_daily_snapshot_1d |
| spot, max_pain_strike | gme_dws_daily_snapshot_1d | max_pain_convergence_pct | gme_dws_daily_snapshot_1d |

### 6.5 Put/Call Ratio

**Definition:** Ratio of total put open interest to total call open interest for standard-class contracts on the nearest standard expiry (same expiry as max pain). Values > 1.0 indicate bearish sentiment; < 1.0 indicate bullish sentiment.

**Scope:** Standard contract class only, scoped to the same nearest expiry as max pain. This ensures comparability with ChartExchange's per-expiry/per-class P/C values.

**Formula:**

```
P/C ratio = SUM(put_OI) / SUM(call_OI)
WHERE contract_class = 'standard' AND expiry = max_pain_expiry
```

**SQL expression** (`gme_dws_daily_snapshot_1d.sql`):

```sql
pc_ratio AS (
    SELECT
        c.pull_date, c.ticker,
        SUM(CASE WHEN c.option_type = 'put' THEN c.open_interest ELSE 0 END) * 1.0
        / NULLIF(SUM(CASE WHEN c.option_type = 'call' THEN c.open_interest ELSE 0 END), 0)
                                                                    AS pc_ratio,
        mp_ref.max_pain_expiry                                      AS pc_ratio_expiry
    FROM gme_dwd_option_contract_di c
    INNER JOIN max_pain mp_ref
        ON c.pull_date = mp_ref.pull_date AND c.ticker = mp_ref.ticker
    WHERE c.contract_class = 'standard'
      AND c.expiry = mp_ref.max_pain_expiry
    GROUP BY c.pull_date, c.ticker, mp_ref.max_pain_expiry
)
```

**Null handling:** `NULLIF(..., 0)` prevents division by zero when no call contracts exist; the ratio returns NULL in that case.

**DQC:** Accepted range test validates `pc_ratio BETWEEN 0 AND 50` (`tests/test_dqc_accepted_ranges.sql`).

**Traceability:**
| Source column | Source model | Target column | Target model |
|--------------|-------------|---------------|--------------|
| open_interest, option_type, contract_class, expiry | gme_dwd_option_contract_di | pc_ratio | gme_dws_daily_snapshot_1d |
| max_pain_expiry | max_pain CTE (from gme_dws_max_pain_by_expiry_1d) | pc_ratio_expiry | gme_dws_daily_snapshot_1d |

### 6.6 Additional Derived Columns

#### Mid Price (`gme_dwd_option_contract_di.sql`, lines 11-14)

```sql
CASE WHEN ods.bid > 0 AND ods.ask > 0
     THEN (ods.bid + ods.ask) / 2.0
     ELSE ods.last_trade_price
END                                                AS mid_price
```

Falls back to last trade price when bid or ask is zero (no valid quote).

#### Days to Expiry (`gme_dwd_option_contract_di.sql`, line 28)

```sql
(ods.expiry - ods.pull_date)                       AS dte
```

#### Series Type (`gme_dwd_option_contract_di.sql`, lines 40-44)

```sql
CASE
    WHEN (ods.expiry - ods.pull_date) > 365 THEN 'LEAP'
    WHEN (ods.expiry - ods.pull_date) <= 7  THEN 'WEEKLY'
    ELSE 'MONTHLY'
END                                                AS series_type
```

#### Top OI Strikes (`gme_dws_daily_snapshot_1d.sql`)

Aggregates open interest by strike for standard-class contracts on the nearest standard expiry (same expiry as max pain). Ranks by total OI descending. Top 3 strikes surfaced in the daily snapshot.

```sql
top_oi AS (
    SELECT
        pull_date, ticker, strike, open_interest,
        ROW_NUMBER() OVER (
            PARTITION BY pull_date, ticker ORDER BY open_interest DESC
        ) AS oi_rank
    FROM (
        SELECT c.pull_date, c.ticker, c.strike, SUM(c.open_interest) AS open_interest
        FROM gme_dwd_option_contract_di c
        INNER JOIN max_pain mp_ref
            ON c.pull_date = mp_ref.pull_date AND c.ticker = mp_ref.ticker
        WHERE c.contract_class = 'standard'
          AND c.expiry = mp_ref.max_pain_expiry
        GROUP BY c.pull_date, c.ticker, c.strike
    )
)
```

### 6.7 ODS Parsing Logic

#### OCC Symbol Parsing (`gme_ods_cboe_options_chain.sql`)

The CBOE API returns raw OCC symbols (e.g., `GME260620C00025000` for standard, `GME1260618C00003000` for adjusted). The ODS model uses **right-anchored parsing** to handle both standard and adjusted roots:

**OCC format:** `{ROOT}{YYMMDD}{C/P}{strike*1000}` — the last 15 characters are always `YYMMDD + C/P + 8-digit strike`. The root length varies (3 for `GME`, 4 for `GME1`, etc.).

**Expiry date** (right-anchored: positions -15 to -10):

```sql
TRY_CAST(
    '20' || SUBSTRING(sym, LENGTH(sym) - 14, 2) || '-' ||
    SUBSTRING(sym, LENGTH(sym) - 12, 2) || '-' ||
    SUBSTRING(sym, LENGTH(sym) - 10, 2)
AS DATE)                                                          AS expiry
```

**Option type** (right-anchored: position -9):

```sql
CASE WHEN SUBSTRING(sym, LENGTH(sym) - 8, 1) = 'C'
     THEN 'call' ELSE 'put' END                                   AS option_type
```

**Strike price** (right-anchored: last 8 digits / 1000):

```sql
TRY_CAST(RIGHT(sym, 8) AS DOUBLE)
    / 1000.0                                                      AS strike
```

#### Contract Class (`gme_dwd_option_contract_di.sql`)

The DWD model classifies contracts as standard or adjusted based on symbol length:

```sql
CASE
    WHEN LENGTH(option_symbol) <= LENGTH(ticker) + 15
    THEN 'standard'
    ELSE 'adjusted'
END                                                AS contract_class
```

Standard OCC symbols have root length equal to ticker length (e.g., `GME` = 3 chars, total = 3 + 15 = 18). Adjusted symbols have longer roots (e.g., `GME1` = 4 chars, total = 4 + 15 = 19+).

---

## 7. Data Sensitivity

| Field / column pattern | Classification | Handling |
|------------------------|---------------|----------|
| All option chain data | public | Freely available delayed market data from CBOE |
| Greeks (delta, gamma, etc.) | public | CBOE-computed, delayed 15 min |

---

## 8. Bidirectional Traceability Matrix

Every SQL expression maps to a TDD field; every TDD metric maps to a model and test.

### 8.1 TDD metric -> SQL model + DQC test

| TDD section | Metric | Model file | Lines | DQC test |
|-------------|--------|------------|-------|----------|
| 6.1 | gex_contribution | models/dwd/gme_dwd_option_contract_di.sql | 32-38 | schema.yml: not_null on gex_contribution |
| 6.2 | call_gex, put_gex, net_gex | models/dws/gme_dws_strike_gex_1d.sql | 8-11 | schema.yml: not_null on net_gex |
| 6.2 | gex_rank | models/dws/gme_dws_strike_gex_1d.sql | 16-19 | schema.yml: not_null on gex_rank |
| 6.3 | net_gex (total) | models/dws/gme_dws_daily_snapshot_1d.sql | 1-11 | (aggregated from tested source) |
| 6.3 | top_gex_strike | models/dws/gme_dws_daily_snapshot_1d.sql | 6-8 | — |
| 6.4 | max_pain_strike | models/dws/gme_dws_max_pain_by_expiry_1d.sql → snapshot via JOIN | — | schema.yml: not_null; test_max_pain_no_mixed_class.sql |
| 6.4 | max_pain_expiry | models/dws/gme_dws_max_pain_by_expiry_1d.sql → snapshot via JOIN | — | schema.yml on ADS |
| 6.4 | max_pain_convergence_pct | models/dws/gme_dws_daily_snapshot_1d.sql | — | — |
| 6.5 | pc_ratio | models/dws/gme_dws_daily_snapshot_1d.sql | — | schema.yml: not_null; test_dqc_accepted_ranges.sql; standard class + nearest expiry |
| 6.5 | pc_ratio_expiry | models/dws/gme_dws_daily_snapshot_1d.sql | — | Same expiry as max_pain_expiry |
| 6.6 | mid_price | models/dwd/gme_dwd_option_contract_di.sql | 11-14 | — |
| 6.6 | dte | models/dwd/gme_dwd_option_contract_di.sql | 28 | — |
| 6.6 | series_type | models/dwd/gme_dwd_option_contract_di.sql | 40-44 | schema.yml: accepted_values [WEEKLY, MONTHLY, LEAP] |
| 6.6 | top_oi_strike_1/2/3 | models/dws/gme_dws_daily_snapshot_1d.sql | 47-56 | — |
| 6.7 | expiry (parsed) | models/ods/gme_ods_cboe_options_chain.sql | 50-54 | — |
| 6.7 | option_type (parsed) | models/ods/gme_ods_cboe_options_chain.sql | 55-56 | schema.yml: accepted_values [call, put] |
| 6.7 | strike (parsed) | models/ods/gme_ods_cboe_options_chain.sql | 57-58 | schema.yml: not_null (warn) |

### 8.2 SQL expression -> TDD section

| Model file | Column | TDD section | Formula reference |
|------------|--------|-------------|-------------------|
| gme_ods_cboe_options_chain.sql | expiry | 6.7 | Right-anchored OCC parse: positions -15 to -10 -> YYMMDD |
| gme_ods_cboe_options_chain.sql | option_type | 6.7 | Right-anchored OCC parse: position -9 -> C/P |
| gme_ods_cboe_options_chain.sql | strike | 6.7 | Right-anchored OCC parse: last 8 digits / 1000 |
| gme_dwd_option_contract_di.sql | contract_class | 6.7 | `LENGTH(symbol) <= LENGTH(ticker) + 15` -> standard/adjusted |
| gme_dwd_option_contract_di.sql | mid_price | 6.6 | (bid + ask) / 2, fallback to last_trade_price |
| gme_dwd_option_contract_di.sql | dte | 6.6 | expiry - pull_date |
| gme_dwd_option_contract_di.sql | gex_contribution | 6.1 | gamma * OI * 100 * spot^2 * 0.01 * sign |
| gme_dwd_option_contract_di.sql | series_type | 6.6 | DTE thresholds: >365=LEAP, <=7=WEEKLY, else=MONTHLY |
| gme_dws_strike_gex_1d.sql | call_gex | 6.2 | SUM(gex_contribution) WHERE option_type='call' |
| gme_dws_strike_gex_1d.sql | put_gex | 6.2 | SUM(gex_contribution) WHERE option_type='put' |
| gme_dws_strike_gex_1d.sql | net_gex | 6.2 | SUM(gex_contribution) |
| gme_dws_strike_gex_1d.sql | gex_rank | 6.2 | ROW_NUMBER by ABS(net_gex) DESC |
| gme_dws_daily_snapshot_1d.sql | net_gex | 6.3 | SUM of strike-level net_gex |
| gme_dws_daily_snapshot_1d.sql | top_gex_strike | 6.3 | Strike with MAX(ABS(net_gex)) |
| gme_dws_max_pain_by_expiry_1d.sql | max_pain_strike | 6.4 | DISTINCT candidates cross-join, MIN(total_pain), per-expiry per-class |
| gme_dws_daily_snapshot_1d.sql | max_pain_strike, max_pain_expiry | 6.4 | JOIN to max_pain_by_expiry WHERE contract_class = 'standard', nearest expiry |
| gme_dws_daily_snapshot_1d.sql | max_pain_convergence_pct | 6.4 | ABS(spot - max_pain) / spot * 100 |
| gme_dws_daily_snapshot_1d.sql | pc_ratio, pc_ratio_expiry | 6.5 | SUM(put_OI) / NULLIF(SUM(call_OI), 0) WHERE standard class + nearest expiry |
| gme_dws_daily_snapshot_1d.sql | top_oi_strike_1/2/3 | 6.6 | Ranked by SUM(OI) per strike DESC, standard class + nearest expiry |
| gme_ads_market_dashboard.sql | all columns | — | Pass-through join of DWS snapshot + DIM date |

---

## 9. Sign-Off Block

| Role | Name | Title / responsibility | Date | Status |
|------|------|-----------------------|------|--------|
| Operator (stakeholder) | (open-source example) | Framework maintainer | 2026-05-21 | approved |
| Customer / consumer | (community) | Framework evaluators | 2026-05-21 | approved |

**Solo-operator exception:** This is an open-source example mart. The framework maintainer serves as both operator and consumer for validation purposes.
