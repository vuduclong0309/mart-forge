WITH snapshot AS (
    SELECT
        pull_date,
        ticker,
        spot,
        max_pain_strike,
        max_pain_convergence_pct,
        net_gex,
        top_gex_strike,
        pc_ratio,
        top_oi_strike_1,
        top_oi_strike_2,
        top_oi_strike_3
    FROM {{ ref('gme_dws_daily_snapshot_1d') }}
),

date_dim AS (
    SELECT
        date_key,
        full_date,
        year,
        quarter,
        month,
        month_name,
        day_of_week,
        day_name,
        is_weekend,
        is_holiday,
        is_trading_day
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
    sn.top_oi_strike_3,

    {{ var('warrant_strike') }}                                     AS warrant_strike,
    {{ var('warrant_quantity') }}                                   AS warrant_qty,
    DATE '{{ var("warrant_expiry") }}'                             AS warrant_expiry,
    (DATE '{{ var("warrant_expiry") }}' - sn.pull_date)            AS warrant_dte,

    GREATEST(0, sn.spot - {{ var('warrant_strike') }})
        * {{ var('warrant_quantity') }}                             AS warrant_intrinsic_value,
    ROUND((sn.spot - {{ var('warrant_strike') }})
        / {{ var('warrant_strike') }} * 100, 2)                    AS warrant_moneyness_pct,

    CASE
        WHEN sn.spot >= {{ var('warrant_strike') }} THEN 'ITM'
        WHEN sn.spot >= {{ var('warrant_strike') }} * 0.9 THEN 'NEAR_MONEY'
        ELSE 'OTM'
    END                                                            AS warrant_moneyness,
    CASE
        WHEN (DATE '{{ var("warrant_expiry") }}' - sn.pull_date) > 120 THEN 'LOW'
        WHEN (DATE '{{ var("warrant_expiry") }}' - sn.pull_date) > 60  THEN 'MEDIUM'
        ELSE 'HIGH'
    END                                                            AS warrant_theta_regime

FROM snapshot sn
LEFT JOIN date_dim d
    ON sn.pull_date = d.full_date
