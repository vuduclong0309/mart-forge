WITH daily AS (
    SELECT
        sn.pull_date,
        sn.ticker,
        sn.spot,
        sn.net_gex,
        sn.pc_ratio,
        m.iv30,
        m.hv20,
        m.dealer_net_gamma
    FROM {{ ref('gme_dws_daily_snapshot_1d') }} sn
    LEFT JOIN {{ ref('gme_dws_options_metrics_1d') }} m
        ON sn.pull_date = m.pull_date AND sn.ticker = m.ticker
)

SELECT
    pull_date,
    ticker,

    ROUND(AVG(spot) OVER w, 4)                                        AS avg_spot_7d,
    ROUND(MIN(spot) OVER w, 4)                                        AS min_spot_7d,
    ROUND(MAX(spot) OVER w, 4)                                        AS max_spot_7d,
    ROUND(
        (spot - FIRST_VALUE(spot) OVER w)
        / NULLIF(FIRST_VALUE(spot) OVER w, 0) * 100,
        2
    )                                                                  AS spot_return_pct_7d,

    ROUND(AVG(net_gex) OVER w, 2)                                     AS avg_net_gex_7d,
    ROUND(AVG(iv30) OVER w, 4)                                        AS avg_iv30_7d,
    ROUND(AVG(pc_ratio) OVER w, 4)                                    AS avg_pc_ratio_7d,
    ROUND(AVG(dealer_net_gamma) OVER w, 2)                            AS avg_dealer_net_gamma_7d,
    ROUND(AVG(hv20) OVER w, 4)                                        AS avg_hv20_7d,

    COUNT(*) OVER w                                                    AS observation_count_7d

FROM daily
WINDOW w AS (
    PARTITION BY ticker
    ORDER BY pull_date
    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
)
