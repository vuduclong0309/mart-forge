# Sign-Off PRD: gme-options-mart

> Generated from `mart.yml`. This is the open-source example mart for the mart-forge framework.

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

## 6. Data Sensitivity

| Field / column pattern | Classification | Handling |
|------------------------|---------------|----------|
| All option chain data | public | Freely available delayed market data from CBOE |
| warrant_* columns | public | Illustrative example values, not real positions |
| Greeks (delta, gamma, etc.) | public | CBOE-computed, delayed 15 min |

---

## 7. Sign-Off Block

| Role | Name | Title / responsibility | Date | Status |
|------|------|-----------------------|------|--------|
| Operator (stakeholder) | (open-source example) | Framework maintainer | 2026-05-21 | approved |
| Customer / consumer | (community) | Framework evaluators | 2026-05-21 | approved |

**Solo-operator exception:** This is an open-source example mart. The framework maintainer serves as both operator and consumer for validation purposes.

**Conditions:** Warrant variables (`warrant_strike`, `warrant_quantity`, `warrant_expiry`) are illustrative defaults. Users should replace them with their own values or remove the ADS warrant columns if not applicable.
