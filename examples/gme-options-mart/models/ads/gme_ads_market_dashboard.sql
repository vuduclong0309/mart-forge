WITH snapshot AS (
    SELECT pull_date, ticker, spot, max_pain_strike, max_pain_expiry, max_pain_convergence_pct,
           net_gex, top_gex_strike, pc_ratio, pc_ratio_expiry, top_oi_strike_1, top_oi_strike_2, top_oi_strike_3
    FROM {{ ref('gme_dws_daily_snapshot_1d') }}
),

metrics AS (
    SELECT pull_date, ticker, gamma_flip_point, iv30, hv20, iv_rank,
           oi_daily_delta, dealer_net_gamma, iv_percentile
    FROM {{ ref('gme_dws_options_metrics_1d') }}
),

sentiment AS (
    SELECT pull_date, ticker, social_mention_count, social_sentiment_score
    FROM {{ ref('gme_dws_social_sentiment_1d') }}
),

trends_7d AS (
    SELECT pull_date, ticker,
           avg_spot_7d, min_spot_7d, max_spot_7d, spot_return_pct_7d,
           avg_net_gex_7d, avg_iv30_7d, avg_pc_ratio_7d,
           avg_dealer_net_gamma_7d, avg_hv20_7d, observation_count_7d
    FROM {{ ref('gme_dws_market_trends_7d') }}
),

trends_30d AS (
    SELECT pull_date, ticker,
           avg_spot_30d, min_spot_30d, max_spot_30d, spot_return_pct_30d,
           avg_net_gex_30d, avg_iv30_30d, avg_pc_ratio_30d,
           avg_dealer_net_gamma_30d, avg_hv20_30d, observation_count_30d
    FROM {{ ref('gme_dws_market_trends_30d') }}
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
    sn.max_pain_expiry,
    sn.max_pain_convergence_pct,
    sn.net_gex,
    sn.top_gex_strike,
    sn.pc_ratio,
    sn.pc_ratio_expiry,
    sn.top_oi_strike_1,
    sn.top_oi_strike_2,
    sn.top_oi_strike_3,

    m.gamma_flip_point,
    m.iv30,
    m.hv20,
    m.iv_rank,
    m.oi_daily_delta,
    m.dealer_net_gamma,
    m.iv_percentile,

    ss.social_mention_count,
    ss.social_sentiment_score,

    t7.avg_spot_7d,
    t7.min_spot_7d,
    t7.max_spot_7d,
    t7.spot_return_pct_7d,
    t7.avg_net_gex_7d,
    t7.avg_iv30_7d,
    t7.avg_pc_ratio_7d,
    t7.avg_dealer_net_gamma_7d,
    t7.avg_hv20_7d,
    t7.observation_count_7d,

    t30.avg_spot_30d,
    t30.min_spot_30d,
    t30.max_spot_30d,
    t30.spot_return_pct_30d,
    t30.avg_net_gex_30d,
    t30.avg_iv30_30d,
    t30.avg_pc_ratio_30d,
    t30.avg_dealer_net_gamma_30d,
    t30.avg_hv20_30d,
    t30.observation_count_30d

FROM snapshot sn
LEFT JOIN metrics m
    ON sn.pull_date = m.pull_date AND sn.ticker = m.ticker
LEFT JOIN sentiment ss
    ON sn.pull_date = ss.pull_date AND sn.ticker = ss.ticker
LEFT JOIN trends_7d t7
    ON sn.pull_date = t7.pull_date AND sn.ticker = t7.ticker
LEFT JOIN trends_30d t30
    ON sn.pull_date = t30.pull_date AND sn.ticker = t30.ticker
LEFT JOIN date_dim d
    ON sn.pull_date = d.full_date
