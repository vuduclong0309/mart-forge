WITH snapshot AS (
    SELECT pull_date, ticker, spot, max_pain_strike, max_pain_convergence_pct,
           net_gex, top_gex_strike, pc_ratio, top_oi_strike_1, top_oi_strike_2, top_oi_strike_3
    FROM {{ ref('gme_dws_daily_snapshot_1d') }}
),

date_dim AS (
    SELECT full_date, year, quarter, month_name, day_name, is_trading_day
    FROM {{ ref('gme_dim_date') }}
)

SELECT
    sn.pull_date,
    sn.ticker,
    sn.spot,

    d.year,
    d.quarter,
    d.month_name,
    d.day_name,
    d.is_trading_day,

    sn.max_pain_strike,
    sn.max_pain_convergence_pct,
    sn.net_gex,
    sn.top_gex_strike,
    sn.pc_ratio,
    sn.top_oi_strike_1,
    sn.top_oi_strike_2,
    sn.top_oi_strike_3

FROM snapshot sn
LEFT JOIN date_dim d
    ON sn.pull_date = d.full_date
