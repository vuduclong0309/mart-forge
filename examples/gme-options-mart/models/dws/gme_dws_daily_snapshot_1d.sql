WITH gex_agg AS (
    SELECT
        pull_date,
        ticker,
        SUM(net_gex)                                                AS net_gex,
        (SELECT strike FROM {{ ref('gme_dws_strike_gex_1d') }} g2
         WHERE g2.pull_date = g1.pull_date AND g2.ticker = g1.ticker
         ORDER BY ABS(g2.net_gex) DESC LIMIT 1)                    AS top_gex_strike
    FROM {{ ref('gme_dws_strike_gex_1d') }} g1
    GROUP BY pull_date, ticker
),

max_pain AS (
    SELECT pull_date, ticker, max_pain_strike, expiry AS max_pain_expiry
    FROM {{ ref('gme_dws_max_pain_by_expiry_1d') }}
    WHERE contract_class = 'standard'
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY pull_date, ticker
        ORDER BY expiry ASC
    ) = 1
),

pc_ratio AS (
    SELECT
        c.pull_date,
        c.ticker,
        SUM(CASE WHEN c.option_type = 'put' THEN c.open_interest ELSE 0 END) * 1.0
        / NULLIF(SUM(CASE WHEN c.option_type = 'call' THEN c.open_interest ELSE 0 END), 0)
                                                                    AS pc_ratio,
        mp_ref.max_pain_expiry                                      AS pc_ratio_expiry
    FROM {{ ref('gme_dwd_option_contract_di') }} c
    INNER JOIN max_pain mp_ref
        ON c.pull_date = mp_ref.pull_date AND c.ticker = mp_ref.ticker
    WHERE c.contract_class = 'standard'
      AND c.expiry = mp_ref.max_pain_expiry
    GROUP BY c.pull_date, c.ticker, mp_ref.max_pain_expiry
),

top_oi AS (
    SELECT
        pull_date, ticker, strike, open_interest,
        ROW_NUMBER() OVER (PARTITION BY pull_date, ticker ORDER BY open_interest DESC) AS oi_rank
    FROM (
        SELECT c.pull_date, c.ticker, c.strike, SUM(c.open_interest) AS open_interest
        FROM {{ ref('gme_dwd_option_contract_di') }} c
        INNER JOIN max_pain mp_ref
            ON c.pull_date = mp_ref.pull_date AND c.ticker = mp_ref.ticker
        WHERE c.contract_class = 'standard'
          AND c.expiry = mp_ref.max_pain_expiry
        GROUP BY c.pull_date, c.ticker, c.strike
    )
),

spot AS (
    SELECT DISTINCT pull_date, ticker, spot
    FROM {{ ref('gme_dwd_option_contract_di') }}
)

SELECT
    s.pull_date,
    s.ticker,
    s.spot,

    mp.max_pain_strike,
    mp.max_pain_expiry,
    ROUND(ABS(s.spot - mp.max_pain_strike) / s.spot * 100, 2)      AS max_pain_convergence_pct,

    ga.net_gex,
    ga.top_gex_strike,

    pc.pc_ratio,
    pc.pc_ratio_expiry,

    (SELECT strike FROM top_oi WHERE pull_date = s.pull_date
     AND ticker = s.ticker AND oi_rank = 1)                         AS top_oi_strike_1,
    (SELECT strike FROM top_oi WHERE pull_date = s.pull_date
     AND ticker = s.ticker AND oi_rank = 2)                         AS top_oi_strike_2,
    (SELECT strike FROM top_oi WHERE pull_date = s.pull_date
     AND ticker = s.ticker AND oi_rank = 3)                         AS top_oi_strike_3

FROM spot s
LEFT JOIN gex_agg ga ON s.pull_date = ga.pull_date AND s.ticker = ga.ticker
LEFT JOIN max_pain mp ON s.pull_date = mp.pull_date AND s.ticker = mp.ticker
LEFT JOIN pc_ratio pc ON s.pull_date = pc.pull_date AND s.ticker = pc.ticker
